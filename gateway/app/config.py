from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    gateway_host: str = "0.0.0.0"
    gateway_port: int = 8100
    database_url: str = "sqlite:///./data/ai_test.db"
    api_key: str = "dev-key"
    engine_default_url: str = "http://127.0.0.1:8200"

    # mvp | milvus  (milvus falls back to mvp if unavailable)
    vector_store: str = "mvp"
    vector_data_dir: str = "./data/vector"
    rag_top_k: int = 5

    # Milvus Lite file path or http://host:19530
    milvus_uri: str = "./data/milvus_rag.db"

    # OpenAI-compatible embeddings (optional). Empty => local hash embedder.
    embedding_base_url: str = ""
    embedding_api_key: str = ""
    embedding_model: str = "text-embedding-3-small"
    embedding_dim: int = 384

    def ensure_dirs(self) -> None:
        Path("data").mkdir(parents=True, exist_ok=True)
        Path(self.vector_data_dir).mkdir(parents=True, exist_ok=True)
        milvus_path = Path(self.milvus_uri)
        if not str(self.milvus_uri).startswith("http"):
            milvus_path.parent.mkdir(parents=True, exist_ok=True)


settings = Settings()
