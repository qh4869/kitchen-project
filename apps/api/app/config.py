from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql+asyncpg://kitchen:kitchen@localhost:5432/kitchen"

    ocr_provider: str = "glm"
    glm_api_key: str = ""
    glm_model: str = "glm-4v"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"

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
