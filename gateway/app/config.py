from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    gateway_host: str = "0.0.0.0"
    gateway_port: int = 8100
    database_url: str = "sqlite:///./data/ai_test.db"
    api_key: str = "dev-key"
    engine_default_url: str = "http://127.0.0.1:8200"
    vector_store: str = "mvp"
    vector_data_dir: str = "./data/vector"
    rag_top_k: int = 5

    def ensure_dirs(self) -> None:
        Path("data").mkdir(parents=True, exist_ok=True)
        Path(self.vector_data_dir).mkdir(parents=True, exist_ok=True)


settings = Settings()
