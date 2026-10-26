from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"


def _default_db_url() -> str:
    db_path = str((BASE_DIR / "agent.db").resolve()).replace("\\", "/")
    return f"sqlite:///{db_path}"


def _write_env_pair(key: str, value: str | None) -> None:
    if value is None:
        return

    lines = ENV_FILE.read_text(encoding="utf-8").splitlines() if ENV_FILE.exists() else []
    updated: list[str] = []
    found = False

    for line in lines:
        if line.strip().startswith(f"{key}="):
            updated.append(f"{key}={value}")
            found = True
        else:
            updated.append(line)

    if not found:
        updated.append(f"{key}={value}")

    ENV_FILE.write_text("\n".join(updated) + "\n", encoding="utf-8")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "AI Personalized Outreach Agent"
    app_version: str = "0.1.0"
    log_level: str = "INFO"

    database_url: str = _default_db_url()
    database_echo: bool = False
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"


@lru_cache
def get_settings() -> Settings:
    return Settings()


def save_gemini_config(api_key: str | None, model: str | None = None) -> Settings:
    settings = get_settings()
    if api_key is not None:
        settings.gemini_api_key = api_key.strip() or None
        if settings.gemini_api_key:
            _write_env_pair("GEMINI_API_KEY", settings.gemini_api_key)
    if model is not None:
        settings.gemini_model = model.strip() or settings.gemini_model
        _write_env_pair("GEMINI_MODEL", settings.gemini_model)
    return settings
