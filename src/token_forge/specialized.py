from __future__ import annotations

import ast
import csv
import io
import re
from decimal import Decimal, InvalidOperation
from typing import Sequence

from .cost import estimate_tokens
from .models import PackResult
from .protection import protected_recall


def _query_terms(query: str) -> tuple[str, ...]:
    ignored = {"the", "and", "for", "with", "review", "code", "summarize", "summary"}
    return tuple(
        term for term in re.findall(r"[A-Za-z0-9_\-]+|[\u3400-\u9fff]+", query.casefold())
        if len(term) > 2 and term not in ignored
    )


def _related(left: str, right: str) -> bool:
    left = left.casefold()
    right = right.casefold()
    if left in right or right in left:
        return True
    prefix = min(len(left), len(right), 6)
    return prefix >= 4 and left[:prefix] == right[:prefix]


def _score_text(text: str, terms: Sequence[str]) -> int:
    words = re.findall(r"[A-Za-z0-9_\-]+|[\u3400-\u9fff]+", text.casefold())
    return sum(any(_related(term, word) for word in words) for term in terms)


def _source_span(lines: list[str], node: ast.AST) -> str:
    first_line = int(getattr(node, "lineno", 1))
    decorators = getattr(node, "decorator_list", ())
    if decorators:
        first_line = min(first_line, *(int(item.lineno) for item in decorators))
    start = max(first_line - 1, 0)
    end = int(getattr(node, "end_lineno", start + 1))
    return "\n".join(lines[start:end]).rstrip()


def _bound_names(node: ast.AST) -> set[str]:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return {node.name}
    if isinstance(node, (ast.Import, ast.ImportFrom)):
        return {alias.asname or alias.name.split(".")[0] for alias in node.names}
    if isinstance(node, (ast.Assign, ast.AnnAssign)):
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        return {child.id for target in targets for child in ast.walk(target) if isinstance(child, ast.Name)}
    return set()


def build_python_context(
    source: str,
    query: str,
    budget_tokens: int,
    protected: Sequence[str],
    source_hash: str,
    cache_key: str,
) -> PackResult | None:
    if len(source.encode("utf-8")) > 16 * 1024 * 1024 or source.count("\n") > 200_000:
        return None
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None
    lines = source.splitlines()
    nodes = [node for node in tree.body if getattr(node, "lineno", None)]
    if not nodes:
        return None
    terms = _query_terms(query)
    spans = {id(node): _source_span(lines, node) for node in nodes}
    bindings = {name: node for node in nodes for name in _bound_names(node)}
    selectable = [node for node in nodes if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]
    selected = {
        id(node): node for node in selectable
        if _score_text(" ".join(_bound_names(node)) + " " + spans[id(node)], terms) > 0
    }
    if not selected:
        return None
    for node in nodes:
        if isinstance(node, ast.ImportFrom) and node.module == "__future__":
            selected[id(node)] = node

    for literal in protected:
        if any(literal in spans[id(node)] for node in selected.values()):
            continue
        candidates = [node for node in nodes if literal in spans[id(node)]]
        if candidates:
            candidate = max(candidates, key=lambda node: (_score_text(spans[id(node)], terms), -int(node.lineno)))
            selected[id(candidate)] = candidate

    changed = True
    while changed:
        changed = False
        referenced = {
            child.id
            for node in selected.values()
            for child in ast.walk(node)
            if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Load)
        }
        for name in referenced:
            dependency = bindings.get(name)
            if dependency is not None and id(dependency) not in selected:
                selected[id(dependency)] = dependency
                changed = True

    ordered = sorted(selected.values(), key=lambda node: int(node.lineno))
    text = "\n\n".join(spans[id(node)] for node in ordered).strip()
    input_tokens = estimate_tokens(source)
    final_tokens = estimate_tokens(text)
    recall = protected_recall(tuple(protected), text)
    syntax_valid = True
    try:
        compile(text, "<token-forge-code-slice>", "exec")
    except SyntaxError:
        syntax_valid = False
    if not text or final_tokens >= input_tokens or final_tokens > budget_tokens or recall < 1.0 or not syntax_valid:
        return None
    return PackResult(
        text=text,
        mode="code-sliced",
        input_tokens=input_tokens,
        final_tokens=final_tokens,
        protected_literals=tuple(protected),
        protected_recall=recall,
        reduction_ratio=1 - final_tokens / input_tokens,
        source_hash=source_hash,
        cache_key=cache_key,
        evidence={
            "syntax_valid": True,
            "source_symbols": len(selectable),
            "selected_symbols": sum(node in selectable for node in ordered),
            "selected_names": sorted(name for node in ordered for name in _bound_names(node)),
            "selection_method": "python-ast-dependency-closure",
        },
    )


def _decimal(value: str) -> Decimal | None:
    try:
        parsed = Decimal(value.strip().replace(",", "")) if value.strip() else None
        return parsed if parsed is not None and parsed.is_finite() else None
    except InvalidOperation:
        return None


def _decimal_places(values: Sequence[str]) -> int:
    return max((len(value.partition(".")[2]) for value in values if "." in value), default=0)


def _format_decimal(value: Decimal, places: int) -> str:
    return format(value, f".{places}f") if places else format(value, "f")


def _markdown_cell(value: str) -> str:
    return re.sub(r"[\r\n]+", " ", value).replace("\\", "\\\\").replace("|", "\\|")


def build_table_context(
    source: str,
    query: str,
    budget_tokens: int,
    protected: Sequence[str],
    source_hash: str,
    cache_key: str,
) -> PackResult | None:
    if len(source.encode("utf-8")) > 64 * 1024 * 1024 or source.count("\n") > 100_001:
        return None
    try:
        dialect = csv.Sniffer().sniff(source[:4096], delimiters=",\t;")
        reader = csv.DictReader(io.StringIO(source), dialect=dialect)
        rows = list(reader)
        headers = tuple(reader.fieldnames or ())
    except (csv.Error, UnicodeError):
        return None
    if (
        not headers or len(headers) > 256 or len(rows) < 2 or any(None in row for row in rows)
        or any(len(str(value)) > 1024 * 1024 for row in rows for value in row.values())
    ):
        return None

    terms = _query_terms(query)
    numeric: dict[str, list[Decimal]] = {}
    raw_numeric: dict[str, list[str]] = {}
    categorical: dict[str, dict[str, int]] = {}
    for header in headers:
        values = [str(row.get(header, "")).strip() for row in rows]
        parsed = [_decimal(value) for value in values]
        header_relevant = any(_related(term, header) for term in terms)
        total_requested = any(term in {"total", "totals", "sum", "amount", "合计", "总计"} for term in terms)
        if all(value is not None for value in parsed) and (header_relevant or total_requested):
            numeric[header] = [value for value in parsed if value is not None]
            raw_numeric[header] = values
        else:
            counts: dict[str, int] = {}
            for value in values:
                counts[value] = counts.get(value, 0) + 1
            if header_relevant and 0 < len(counts) <= 20:
                categorical[header] = counts
    if not numeric and not categorical:
        return None

    lines = [
        "# Table query context", "", f"- Source rows: {len(rows)}",
        f"- Query: {query}", "", "## Schema", "", ", ".join(headers),
    ]
    if numeric:
        lines.extend(["", "## Numeric aggregates", "", "| Column | Count | Sum | Min | Max |", "|---|---:|---:|---:|---:|"])
        for header, values in numeric.items():
            places = _decimal_places(raw_numeric[header])
            lines.append(
                f"| {header} | {len(values)} | {_format_decimal(sum(values, Decimal(0)), places)} "
                f"| {_format_decimal(min(values), places)} | {_format_decimal(max(values), places)} |"
            )
    for header, counts in categorical.items():
        lines.extend(["", f"## Counts by `{header}`", "", "| Value | Rows |", "|---|---:|"])
        lines.extend(f"| {_markdown_cell(value)} | {count} |" for value, count in sorted(counts.items()))
    text = "\n".join(lines).rstrip() + "\n"
    input_tokens = estimate_tokens(source)
    final_tokens = estimate_tokens(text)
    recall = protected_recall(tuple(protected), text)
    reconciled = all(len(values) == len(rows) for values in numeric.values())
    if final_tokens >= input_tokens or final_tokens > budget_tokens or recall < 1.0 or not reconciled:
        return None
    return PackResult(
        text=text,
        mode="table-aggregated",
        input_tokens=input_tokens,
        final_tokens=final_tokens,
        protected_literals=tuple(protected),
        protected_recall=recall,
        reduction_ratio=1 - final_tokens / input_tokens,
        source_hash=source_hash,
        cache_key=cache_key,
        evidence={
            "source_rows": len(rows),
            "aggregated_rows": len(rows),
            "aggregation_reconciled": reconciled,
            "numeric_columns": sorted(numeric),
            "categorical_columns": sorted(categorical),
            "selection_method": "csv-schema-aware-aggregate",
        },
    )
