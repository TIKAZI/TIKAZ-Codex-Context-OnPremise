from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence


_TOKEN_RE = re.compile(r"[A-Za-z0-9_./:-]+|[\u3400-\u9fff]+")

_ENGLISH_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "because", "by", "do", "for",
    "from", "has", "have", "how", "in", "into", "is", "it", "keeping", "make",
    "no", "not", "of", "on", "or", "prepare", "review", "should", "so", "than",
    "that", "the", "their", "then", "they", "this", "through", "to", "use", "was",
    "what", "when", "while", "with", "without",
}

_LEXICAL_ALIASES: Mapping[str, tuple[str, ...]] = {
    "backup": ("back up", "snapshot"),
    "cause": ("root cause", "reason"),
    "mitigation": ("fix", "repair", "remediation"),
    "owner": ("responsible", "assignee"),
    "rollback": ("roll back", "revert"),
    "validation": ("validate", "verify", "verification", "check"),
    "verification": ("verify", "validate", "validation", "check"),
}

_FACET_MIN_MATCH: Mapping[str, int] = {
    "ocr-fallback": 2,
    "scan-detection": 2,
}


@dataclass(frozen=True)
class EvidenceFacet:
    name: str
    terms: tuple[str, ...]


@dataclass(frozen=True)
class QueryPlan:
    original_terms: tuple[str, ...]
    bridge_terms: tuple[str, ...]
    facets: tuple[EvidenceFacet, ...]


@dataclass(frozen=True)
class EvidenceSelection:
    items: tuple[Mapping[str, object], ...]
    status: str
    facet_coverage: float
    confidence: float


_INTENT_FACET_RULES: tuple[
    tuple[tuple[str, ...], tuple[tuple[str, tuple[str, ...]], ...]], ...
] = (
    (
        ("without a mouse", "no mouse", "无鼠标", "不用鼠标"),
        (
            ("keyboard-navigation", ("keyboard", "navigation", "键盘", "导航")),
            ("visible-focus", ("focus", "visible indicator", "焦点", "指示")),
            ("semantic-labels", ("semantic labels", "assistive technology", "meaningful names", "语义标签", "辅助技术")),
        ),
    ),
    (
        ("readable on a phone", "on a phone", "mobile", "手机", "窄屏"),
        (
            ("responsive-layout", ("responsive", "breakpoint", "narrow screen", "overflow", "响应式", "窄屏", "溢出")),
            ("readable-type", ("readable", "typography", "contrast", "mobile size", "排版", "对比度", "字号")),
        ),
    ),
    (
        ("smallest useful", "keeping proof", "保留证据", "最小有用", "有界上下文"),
        (
            ("task-selection", ("select", "passage", "requested task", "directly support", "选择", "任务")),
            ("source-anchor", ("anchor", "citation", "retained excerpt", "锚点", "引用")),
            ("protected-facts", ("protected", "facts", "exact commands", "urls", "受保护事实", "命令", "网址")),
            ("budget", ("pack", "declared budget", "within budget", "上下文包", "预算")),
            ("omissions", ("omitted", "unresolved visual", "explicitly", "遗漏", "待核验视觉")),
        ),
    ),
    (
        ("encrypted traffic", "machine identity", "no longer valid", "certificate recovery", "证书失效", "加密流量"),
        (
            ("failure-cause", ("expired", "tls handshake", "failing", "过期", "握手失败")),
            ("credential-rotation", ("rotate", "renew", "secret store", "轮换", "续期")),
            ("runtime-reload", ("restart", "workers", "load renewed", "reload", "重启", "加载")),
            ("service-validation", ("validate", "checkout", "login", "https endpoint", "repaired endpoint", "验证", "登录")),
            ("recurrence-prevention", ("expiry monitoring", "prevent recurrence", "alert", "到期监控", "防止复发")),
        ),
    ),
    (
        ("no copyable text", "without text layer", "没有可复制文字", "无文字层", "扫描件"),
        (
            ("scan-detection", ("scan", "text layer", "detect", "扫描", "文字层", "检测")),
            ("ocr-fallback", ("ocr", "fallback", "confidence", "回退", "置信度")),
            ("table-fidelity", ("table cell", "complex table", "表格单元格", "复杂表格")),
            ("image-evidence", ("source image", "illustration", "visual evidence", "原图", "插图", "视觉证据")),
            ("source-anchor", ("anchor", "page anchor", "锚点", "页码锚点")),
        ),
    ),
)

_QUERY_FACETS: tuple[tuple[tuple[str, ...], tuple[str, ...]], ...] = (
    (("encrypted traffic", "machine identity", "no longer valid", "证书失效", "加密流量"),
     ("certificate", "tls", "https", "credential", "证书", "凭据")),
    (("without a mouse", "no mouse", "无鼠标", "不用鼠标"),
     ("keyboard", "focus", "semantic labels", "accessibility", "键盘", "焦点", "语义标签")),
    (("phone", "mobile", "手机", "窄屏"),
     ("responsive", "mobile", "typography", "contrast", "响应式", "排版", "对比度")),
    (("no copyable text", "without text layer", "没有可复制文字", "无文字层", "扫描件"),
     ("ocr", "scan", "text layer", "fallback", "扫描", "文字层", "回退")),
    (("table", "illustration", "image", "表格", "插图", "图片"),
     ("table cells", "visual evidence", "source image", "表格单元格", "视觉证据", "原图")),
    (("proof", "evidence", "证明", "证据", "保住", "保留"),
     ("evidence", "anchor", "citation", "traceability", "omitted", "来源锚点", "引用", "遗漏")),
    (("smallest useful", "bounded", "最小有用", "有界"),
     ("selection", "budget", "protected facts", "omitted", "选择", "预算", "受保护事实", "遗漏")),
)


def _english_forms(value: str) -> tuple[str, ...]:
    forms = [value]
    if len(value) > 4 and value.endswith("ies"):
        forms.append(f"{value[:-3]}y")
    elif len(value) > 3 and value.endswith("s") and not value.endswith("ss"):
        forms.append(value[:-1])
    return tuple(forms)


def retrieval_terms(text: str) -> tuple[str, ...]:
    """Return stable lexical terms, including bounded CJK n-grams."""
    terms: list[str] = []
    for raw in _TOKEN_RE.findall(text.casefold()):
        if re.fullmatch(r"[\u3400-\u9fff]+", raw):
            if len(raw) <= 4:
                terms.append(raw)
            for size in (2, 3, 4):
                terms.extend(raw[index:index + size] for index in range(len(raw) - size + 1))
        elif len(raw) > 1 and raw not in _ENGLISH_STOPWORDS:
            terms.extend(_english_forms(raw))
            for part in re.split(r"[_./:-]+", raw):
                if len(part) > 1 and part not in _ENGLISH_STOPWORDS:
                    terms.extend(_english_forms(part))
    return tuple(dict.fromkeys(terms))


def _facet_terms(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(term for value in values for term in retrieval_terms(value)))


def build_query_plan(
    text: str,
    *,
    query_variants: Sequence[str] = (),
) -> QueryPlan:
    """Build a bounded, auditable lexical plan without a model dependency."""
    if len(query_variants) > 5 or any(len(value) > 240 for value in query_variants):
        raise ValueError("query variants are limited to five hints of at most 240 characters")
    original = retrieval_terms(text)
    lowered = text.casefold()
    facets: list[EvidenceFacet] = []
    facet_names: set[str] = set()
    bridge_terms: list[str] = []

    for triggers, definitions in _INTENT_FACET_RULES:
        if not any(trigger.casefold() in lowered for trigger in triggers):
            continue
        for name, values in definitions:
            terms = _facet_terms(values)
            bridge_terms.extend(terms)
            if name not in facet_names:
                facets.append(EvidenceFacet(name=name, terms=terms))
                facet_names.add(name)

    for triggers, additions in _QUERY_FACETS:
        if any(trigger.casefold() in lowered for trigger in triggers):
            bridge_terms.extend(_facet_terms(additions))

    for index, variant in enumerate(query_variants, 1):
        terms = retrieval_terms(variant)
        bridge_terms.extend(terms)
        if terms:
            facets.append(EvidenceFacet(name=f"caller-variant-{index}", terms=terms))

    if not facets:
        generic_facets: list[EvidenceFacet] = []
        for term in original:
            aliases = _facet_terms(_LEXICAL_ALIASES.get(term, ()))
            bridge_terms.extend(aliases)
            generic_facets.append(EvidenceFacet(
                name=f"term:{term}",
                terms=tuple(dict.fromkeys((term, *aliases))),
            ))
        facets = generic_facets

    return QueryPlan(
        original_terms=original,
        bridge_terms=tuple(dict.fromkeys(bridge_terms)),
        facets=tuple(facets),
    )


def expanded_query_terms(text: str) -> tuple[str, ...]:
    plan = build_query_plan(text)
    return tuple(dict.fromkeys((*plan.original_terms, *plan.bridge_terms)))


def _term_counts(text: str) -> Counter[str]:
    return Counter(retrieval_terms(text))


def lexical_rank(
    chunks: Sequence[Mapping[str, object]],
    query: str,
    *,
    query_variants: Sequence[str] = (),
) -> list[dict[str, object]]:
    plan = build_query_plan(query, query_variants=query_variants)
    query_terms = tuple(dict.fromkeys((*plan.original_terms, *plan.bridge_terms)))
    original_set = set(plan.original_terms)
    bridge_set = set(plan.bridge_terms)
    document_terms = [_term_counts(str(chunk.get("text", ""))) for chunk in chunks]
    document_count = max(1, len(document_terms))
    document_frequency = Counter({
        term: sum(counts.get(term, 0) > 0 for counts in document_terms)
        for term in query_terms
    })
    average_length = (
        sum(sum(counts.values()) for counts in document_terms) / document_count
        if document_terms else 1.0
    )
    facet_terms = {facet.name: set(facet.terms) for facet in plan.facets}
    ranked: list[dict[str, object]] = []
    for chunk, counts in zip(chunks, document_terms):
        score = 0.0
        matched: list[str] = []
        document_length = max(1, sum(counts.values()))
        for term in query_terms:
            tf = counts.get(term, 0)
            if not tf:
                continue
            matched.append(term)
            inverse = math.log(
                1 + (document_count - document_frequency[term] + 0.5)
                / (document_frequency[term] + 0.5)
            )
            saturation = (tf * 2.2) / (
                tf + 1.2 * (0.25 + 0.75 * document_length / max(average_length, 1.0))
            )
            if bridge_set and term in bridge_set:
                term_weight = 1.45
            elif bridge_set and term in original_set:
                term_weight = 0.55
            else:
                term_weight = 1.0
            score += term_weight * inverse * saturation * (1 + min(len(term), 12) / 24)
        count_terms = set(counts)
        facet_hits = tuple(
            name
            for name, terms in facet_terms.items()
            if (
                len(count_terms & terms) >= max(1, math.ceil(len(terms) * 0.5))
                if name.startswith("caller-variant-")
                else len(count_terms & terms) >= _FACET_MIN_MATCH.get(name, 1)
            )
        )
        if plan.facets:
            score += 1.25 * len(facet_hits)
        ranked.append({
            "id": str(chunk["id"]),
            "index": int(chunk["index"]),
            "lexical_score": score,
            "matched_terms": matched,
            "matched_original_terms": tuple(term for term in matched if term in original_set),
            "matched_bridge_terms": tuple(term for term in matched if term in bridge_set),
            "facet_hits": facet_hits,
        })
    ranked.sort(key=lambda item: (-float(item["lexical_score"]), int(item["index"])))
    return ranked


def _jaccard(left: Iterable[str], right: Iterable[str]) -> float:
    left_set, right_set = set(left), set(right)
    union = left_set | right_set
    return len(left_set & right_set) / len(union) if union else 0.0


def fuse_and_diversify(
    chunks: Sequence[Mapping[str, object]],
    query: str,
    *,
    model_ranked: Sequence[Mapping[str, object]] = (),
    query_variants: Sequence[str] = (),
    diversity_weight: float = 0.08,
    model_weight: float = 1.0,
    coverage_weight: float = 0.20,
    new_coverage_weight: float = 0.10,
    facet_weight: float = 0.80,
    new_facet_weight: float = 0.55,
) -> list[dict[str, object]]:
    """Fuse lexical and semantic ranks, then apply deterministic MMR selection."""
    plan = build_query_plan(query, query_variants=query_variants)
    lexical = lexical_rank(chunks, query, query_variants=query_variants)
    lexical_positions = {str(item["id"]): rank for rank, item in enumerate(lexical, 1)}
    lexical_by_id = {str(item["id"]): item for item in lexical}
    model_positions = {str(item["id"]): rank for rank, item in enumerate(model_ranked, 1)}
    by_id = {str(chunk["id"]): chunk for chunk in chunks}
    query_terms = set((*plan.original_terms, *plan.bridge_terms))
    facet_names = {facet.name for facet in plan.facets}
    remaining: dict[str, dict[str, Any]] = {}
    for chunk_id, chunk in by_id.items():
        rrf = 1 / (60 + lexical_positions[chunk_id])
        if chunk_id in model_positions:
            rrf += model_weight / (60 + model_positions[chunk_id])
        terms = set(retrieval_terms(str(chunk.get("text", ""))))
        coverage = len(query_terms & terms) / len(query_terms) if query_terms else 0.0
        lexical_item = lexical_by_id[chunk_id]
        facet_hits = set(str(value) for value in lexical_item.get("facet_hits", ()))
        remaining[chunk_id] = {
            "id": chunk_id,
            "index": int(chunk["index"]),
            "rrf_score": rrf,
            "query_coverage": coverage,
            "terms": terms,
            "lexical_score": float(lexical_item["lexical_score"]),
            "matched_terms": tuple(lexical_item.get("matched_terms", ())),
            "matched_original_terms": tuple(lexical_item.get("matched_original_terms", ())),
            "matched_bridge_terms": tuple(lexical_item.get("matched_bridge_terms", ())),
            "facet_hits": facet_hits,
        }

    selected: list[dict[str, Any]] = []
    covered: set[str] = set()
    covered_facets: set[str] = set()
    while remaining:
        best = max(
            remaining.values(),
            key=lambda item: (
                10 * item["rrf_score"]
                + coverage_weight * item["query_coverage"]
                + new_coverage_weight * (
                    len((item["terms"] & query_terms) - covered) / len(query_terms)
                    if query_terms else 0.0
                )
                + facet_weight * (
                    len(item["facet_hits"]) / len(facet_names) if facet_names else 0.0
                )
                + new_facet_weight * (
                    len(item["facet_hits"] - covered_facets) / len(facet_names)
                    if facet_names else 0.0
                )
                - diversity_weight * max(
                    (_jaccard(item["terms"], prior["terms"]) for prior in selected),
                    default=0.0,
                ),
                item["query_coverage"],
                -item["index"],
            ),
        )
        selected.append(best)
        covered.update(best["terms"] & query_terms)
        covered_facets.update(best["facet_hits"])
        del remaining[best["id"]]

    return [
        {
            key: tuple(sorted(value)) if key == "facet_hits" else value
            for key, value in item.items() if key != "terms"
        }
        for item in selected
    ]


def select_evidence(
    ranked: Sequence[Mapping[str, object]],
    query: str,
    *,
    query_variants: Sequence[str] = (),
    covered_facets: Iterable[str] = (),
    min_items: int = 1,
    max_items: int = 5,
) -> EvidenceSelection:
    """Select only items that add query evidence or a new evidence facet."""
    if min_items < 0 or max_items < 1 or min_items > max_items:
        raise ValueError("selection bounds must satisfy 0 <= min_items <= max_items")
    plan = build_query_plan(query, query_variants=query_variants)
    required = {facet.name for facet in plan.facets}
    has_explicit_facets = bool(query_variants) or any(
        not facet.name.startswith("term:") for facet in plan.facets
    )
    selected: list[Mapping[str, object]] = []
    covered = {str(value) for value in covered_facets} & required

    if required and covered >= required:
        return EvidenceSelection((), "matched", 1.0, 1.0)

    for item in ranked:
        score = float(item.get("lexical_score", 0.0))
        hits = {str(value) for value in item.get("facet_hits", ())}
        new_hits = hits - covered
        if score <= 0 and not hits:
            continue
        if has_explicit_facets and len(selected) >= min_items and not new_hits:
            continue
        selected.append(item)
        covered.update(hits)
        if len(selected) >= max_items or (
            has_explicit_facets and required and covered >= required
        ):
            break

    coverage = len(covered & required) / len(required) if required else 1.0
    if not selected:
        status = "partial-evidence" if coverage > 0 else "insufficient-evidence"
        return EvidenceSelection((), status, coverage, coverage)
    status = "matched" if coverage >= 0.999 else "partial-evidence"
    positive = sum(float(item.get("lexical_score", 0.0)) > 0 for item in selected)
    confidence = coverage * (positive / len(selected))
    return EvidenceSelection(tuple(selected), status, coverage, confidence)


def query_coverage(query: str, texts: Iterable[str]) -> float:
    required = set(expanded_query_terms(query))
    if not required:
        return 1.0
    present: set[str] = set()
    for text in texts:
        present.update(retrieval_terms(text))
    return len(required & present) / len(required)


def retrieval_metrics(
    ranked_ids: Sequence[str],
    relevance: Mapping[str, int],
    *,
    k_values: Sequence[int] = (1, 3, 5),
) -> dict[str, float]:
    relevant_ids = {item_id for item_id, grade in relevance.items() if grade > 0}
    output: dict[str, float] = {}
    for k in k_values:
        top = ranked_ids[:k]
        hits = sum(item_id in relevant_ids for item_id in top)
        output[f"recall_at_{k}"] = hits / len(relevant_ids) if relevant_ids else 1.0
        output[f"precision_at_{k}"] = hits / k if k else 0.0
        dcg = sum(
            (2 ** relevance.get(item_id, 0) - 1) / math.log2(rank + 1)
            for rank, item_id in enumerate(top, 1)
        )
        ideal = sorted((grade for grade in relevance.values() if grade > 0), reverse=True)[:k]
        idcg = sum((2 ** grade - 1) / math.log2(rank + 1) for rank, grade in enumerate(ideal, 1))
        output[f"ndcg_at_{k}"] = dcg / idcg if idcg else 1.0
    first = next((rank for rank, item_id in enumerate(ranked_ids, 1) if item_id in relevant_ids), None)
    output["mrr"] = 1 / first if first else 0.0
    return output
