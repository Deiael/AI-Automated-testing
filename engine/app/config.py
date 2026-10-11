from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_ENGINE_DIR = Path(__file__).resolve().parents[1]
_ENV_FILE = _ENGINE_DIR / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8-sig",
        extra="ignore",
    )

    engine_host: str = "0.0.0.0"
    engine_port: int = 8200

    # OpenAI-compatible（DeepSeek / 通义 / OpenAI 等）
    openai_api_key: str = ""
    openai_base_url: str = "https://api.deepseek.com/v1"
    openai_model: str = "deepseek-chat"
    # false：始终用引擎 .env 的 model（推荐）；true：允许网关 EngineProfile.model 覆盖
    allow_model_override: bool = False
    # LLM 失败时是否回退 Mock（联调 DeepSeek 时建议 false，便于暴露真实错误）
    llm_fallback_mock: bool = False
    llm_timeout_seconds: float = 90.0
    llm_temperature: float = 0.2

    @property
    def llm_enabled(self) -> bool:
        return bool(self.openai_api_key.strip().strip('"').strip("'"))


settings = Settings()
