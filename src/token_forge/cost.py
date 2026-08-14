from __future__ import annotations

import math
import re


_CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")


def estimate_tokens(text: str) -> int:
    """Return a deterministic estimate, never provider telemetry."""
    if not text:
        return 0
    cjk = len(_CJK_RE.findall(text))
    non_cjk = len(_CJK_RE.sub("", text).encode("utf-8"))
    return max(1, cjk + math.ceil(non_cjk / 4))

