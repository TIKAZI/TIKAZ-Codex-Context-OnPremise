from __future__ import annotations

import re


PATTERNS = (
    re.compile(r"`([^`\r\n]+)`"),
    re.compile(r"https?://[^\s<>\]\[(){}\"']+"),
    re.compile(r"\bv?\d+(?:\.\d+){1,4}(?:[-+][A-Za-z0-9.-]+)?\b", re.IGNORECASE),
    re.compile(r"\b\d{4}-\d{2}-\d{2}\b"),
    re.compile(r"\b\d+(?:\.\d+)?\b"),
    re.compile(r"\b[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+\b"),
)


def extract_protected_literals(text: str) -> tuple[str, ...]:
    matches: list[tuple[int, str]] = []
    for pattern in PATTERNS:
        for match in pattern.finditer(text):
            value = match.group(1) if pattern.pattern.startswith("`") else match.group(0)
            value = value.rstrip(".,;:!?")
            if value:
                matches.append((match.start(), value))

    seen: set[str] = set()
    ordered: list[str] = []
    for _, value in sorted(matches, key=lambda item: item[0]):
        if value not in seen:
            seen.add(value)
            ordered.append(value)
    return tuple(ordered)


def protected_recall(protected: tuple[str, ...], output: str) -> float:
    if not protected:
        return 1.0
    return sum(value in output for value in protected) / len(protected)

