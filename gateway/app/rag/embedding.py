from __future__ import annotations

import hashlib
import logging
import math
import re
from collections import Counter

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_TOKEN_RE = re.compile(r"[\w\u4e00-\u9fff]+", re.UNICODE)


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    if settings.embedding_base_url and settings.embedding_api_key:
        try:
            return _embed_openai_compatible(texts)
        except Exception:
            logger.exception("embedding API failed; falling back to local hasher")
    return [_local_embed(t, settings.embedding_dim) for t in texts]


def embed_query(text: str) -> list[float]:
    return embed_texts([text])[0]


def _embed_openai_compatible(texts: list[str]) -> list[list[float]]:
    base = settings.embedding_base_url.rstrip("/")
    url = f"{base}/embeddings" if base.endswith("/v1") else f"{base}/v1/embeddings"
    headers = {"Authorization": f"Bearer {settings.embedding_api_key}", "Content-Type": "application/json"}
    payload = {"model": settings.embedding_model, "input": texts}
    with httpx.Client(timeout=60.0) as client:
        resp = client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()["data"]
        data = sorted(data, key=lambda x: x["index"])
        vectors = [row["embedding"] for row in data]
        # normalize dim if needed
        dim = settings.embedding_dim
        out: list[list[float]] = []
        for v in vectors:
            if len(v) == dim:
                out.append(v)
            elif len(v) > dim:
                out.append(v[:dim])
            else:
                out.append(v + [0.0] * (dim - len(v)))
        return out


def _tokenize(text: str) -> list[str]:
    parts = _TOKEN_RE.findall((text or "").lower())
    tokens: list[str] = []
    for p in parts:
        if re.fullmatch(r"[\u4e00-\u9fff]+", p) and len(p) > 1:
            tokens.extend(list(p))
            tokens.append(p)
        else:
            tokens.append(p)
    return tokens


def _local_embed(text: str, dim: int) -> list[float]:
    """Deterministic bag-of-words hashing to fixed-dim unit vector (no external model)."""
    vec = [0.0] * dim
    counts = Counter(_tokenize(text))
    if not counts:
        vec[0] = 1.0
        return vec
    for token, cnt in counts.items():
        h = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16)
        idx = h % dim
        sign = 1.0 if (h >> 8) & 1 else -1.0
        vec[idx] += sign * float(cnt)
    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [x / norm for x in vec]
