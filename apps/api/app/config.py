from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql+asyncpg://kitchen:kitchen@localhost:5432/kitchen"

    # LLM (OpenAI-compatible; default points at 火山方舟 Ark)
    ocr_provider: str = "volcengine"          # volcengine | openai | mock
    llm_base_url: str = "https://ark.cn-beijing.volces.com/api/v3"
    # Accepts either LLM_API_KEY (in .env) or ARK_API_KEY_KITCHEN (shell env, preferred for secrets)
    llm_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("LLM_API_KEY", "ARK_API_KEY_KITCHEN"),
    )
    llm_model: str = "Doubao-Seed-2.0-mini"
    llm_force_json: bool = True
    ocr_mock_fixture: str = ""                # path to JSON fixture for MockOcrAdapter

    storage_driver: str = "local"
    upload_dir: str = "./uploads"

    api_host: str = "0.0.0.0"
    api_port: int = 3000
    web_origin: str = "http://localhost:5173"

    @property
    def upload_path(self) -> Path:
        p = Path(self.upload_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p


settings = Settings()
