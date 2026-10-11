from __future__ import annotations

from typing import Any


def score_test_case(case: dict[str, Any], schema: dict[str, Any] | None = None, rag_texts: list[str] | None = None) -> float:
    """Gateway-side confidence; never computed in engine persistence."""
    required = (schema or {}).get("required") or ["title", "steps", "expected"]
    present = sum(1 for k in required if _has(case, k))
    completeness = present / max(1, len(required))

    schema_bonus = 0.1 if not case.get("_schema_missing") else -0.2

    rag_hit = 0.0
    blob = " ".join(
        [
            str(case.get("title") or ""),
            str(case.get("expected") or ""),
            " ".join(case.get("steps") or []) if isinstance(case.get("steps"), list) else str(case.get("steps") or ""),
        ]
    )
    for t in rag_texts or []:
        if t and t[:20] in blob:
            rag_hit = 0.15
            break
        # loose overlap
        overlap = len(set(blob) & set(t[:80]))
        if overlap > 8:
            rag_hit = max(rag_hit, 0.08)

    score = max(0.0, min(1.0, 0.55 * completeness + 0.25 + schema_bonus + rag_hit))
    return round(score, 3)


def _has(case: dict[str, Any], key: str) -> bool:
    v = case.get(key)
    if v is None:
        return False
    if isinstance(v, str):
        return bool(v.strip())
    if isinstance(v, list):
        return len(v) > 0
    return True
