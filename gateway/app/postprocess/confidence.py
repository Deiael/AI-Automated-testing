from __future__ import annotations

from typing import Any


EXECUTABLE_FIELDS = ("method", "path", "assert")
CORE_FIELDS = ("title", "steps", "expected")


def score_test_case(
    case: dict[str, Any],
    schema: dict[str, Any] | None = None,
    rag_texts: list[str] | None = None,
) -> float:
    """Gateway-side confidence; never computed in engine persistence."""
    return score_test_case_detail(case, schema, rag_texts)["score"]


def score_test_case_detail(
    case: dict[str, Any],
    schema: dict[str, Any] | None = None,
    rag_texts: list[str] | None = None,
) -> dict[str, Any]:
    required = (schema or {}).get("required") or list(CORE_FIELDS)
    present = sum(1 for k in required if _has(case, k))
    completeness = present / max(1, len(required))

    executable_present = sum(1 for k in EXECUTABLE_FIELDS if _has(case, k))
    executable = executable_present / len(EXECUTABLE_FIELDS)

    schema_penalty = 0.2 if case.get("_schema_missing") else 0.0
    rag_hit = _rag_overlap(case, rag_texts or [])

    score = 0.45 * completeness + 0.30 * executable + 0.15 * rag_hit + 0.10
    score -= schema_penalty
    score = max(0.0, min(1.0, score))
    rounded = round(score, 3)
    return {
        "score": rounded,
        "completeness": round(completeness, 3),
        "executable": round(executable, 3),
        "rag_hit": round(rag_hit, 3),
        "schema_ok": not bool(case.get("_schema_missing")),
        "missing": list(case.get("_schema_missing") or []),
        "band": confidence_band(rounded),
    }


def confidence_band(score: float) -> str:
    if score >= 0.8:
        return "high"
    if score >= 0.6:
        return "medium"
    return "low"


def summarize_confidences(scores: list[float]) -> dict[str, Any]:
    values = [float(s) for s in scores if s is not None]
    if not values:
        return {
            "count": 0,
            "avg": 0.0,
            "min": 0.0,
            "max": 0.0,
            "high": 0,
            "medium": 0,
            "low": 0,
        }
    bands = [confidence_band(v) for v in values]
    return {
        "count": len(values),
        "avg": round(sum(values) / len(values), 3),
        "min": round(min(values), 3),
        "max": round(max(values), 3),
        "high": bands.count("high"),
        "medium": bands.count("medium"),
        "low": bands.count("low"),
    }


def _rag_overlap(case: dict[str, Any], rag_texts: list[str]) -> float:
    blob = " ".join(
        [
            str(case.get("title") or ""),
            str(case.get("expected") or ""),
            " ".join(case.get("steps") or []) if isinstance(case.get("steps"), list) else str(case.get("steps") or ""),
            str(case.get("path") or ""),
        ]
    )
    if not blob.strip() or not rag_texts:
        return 0.0
    hit = 0.0
    for text in rag_texts:
        if not text:
            continue
        snippet = text[:24]
        if snippet and snippet in blob:
            return 1.0
        overlap = len(set(blob.lower()) & set(text[:120].lower()))
        if overlap > 12:
            hit = max(hit, 0.55)
        elif overlap > 6:
            hit = max(hit, 0.3)
    return hit


def _has(case: dict[str, Any], key: str) -> bool:
    v = case.get(key)
    if v is None:
        return False
    if isinstance(v, str):
        return bool(v.strip())
    if isinstance(v, list):
        return len(v) > 0
    if isinstance(v, dict):
        return len(v) > 0
    return True
