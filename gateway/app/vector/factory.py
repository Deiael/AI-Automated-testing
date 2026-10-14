from __future__ import annotations

import logging

from app.config import settings
from app.vector.mvp_store import MvpVectorStore

logger = logging.getLogger(__name__)


def get_vector_store(kind: str | None = None, root: str | None = None):
    kind = (kind or settings.vector_store or "mvp").lower()
    root = root or settings.vector_data_dir
    if kind == "milvus":
        try:
            from app.vector.milvus_store import MilvusVectorStore

            return MilvusVectorStore(uri=settings.milvus_uri)
        except Exception:
            logger.exception("Milvus unavailable; falling back to mvp store")
            return MvpVectorStore(root)
    return MvpVectorStore(root)
