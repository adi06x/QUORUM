from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "QUORUM API"
    app_env: str = "development"
    api_prefix: str = "/api"
    sqlite_path: str = "data/quorum.db"
    chroma_path: str = "data/chroma"
    llm_api_key: str | None = Field(default=None, alias="LLM_API_KEY")
    llm_base_url: str = Field(default="https://api.openai.com/v1", alias="LLM_BASE_URL")
    llm_model: str = Field(default="gpt-4.1-mini", alias="LLM_MODEL")
    llm_timeout_seconds: int = 90
    semantic_scholar_api_key: str | None = Field(default=None, alias="SEMANTIC_SCHOLAR_API_KEY")
    default_confidence_threshold: float = Field(default=0.74, alias="DEFAULT_CONFIDENCE_THRESHOLD")
    max_research_passes: int = Field(default=2, alias="MAX_RESEARCH_PASSES")
    max_sources_per_provider: int = 4
    enable_demo_mode: bool = Field(default=True, alias="ENABLE_DEMO_MODE")
    frontend_origin: str = Field(default="http://localhost:4173", alias="FRONTEND_ORIGIN")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    @property
    def backend_root(self) -> Path:
        return Path(__file__).resolve().parents[1]

    @property
    def sqlite_file(self) -> Path:
        return self._resolve_path(self.sqlite_path)

    @property
    def chroma_dir(self) -> Path:
        return self._resolve_path(self.chroma_path)

    def _resolve_path(self, raw_path: str) -> Path:
        path = Path(raw_path)
        if path.is_absolute():
            return path
        return (self.backend_root / path).resolve()


@lru_cache
def get_settings() -> Settings:
    return Settings()

