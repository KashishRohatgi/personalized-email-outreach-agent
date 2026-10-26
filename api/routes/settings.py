from fastapi import APIRouter
from pydantic import BaseModel

from config.settings import get_settings, save_gemini_config

router = APIRouter(prefix="/settings", tags=["settings"])


class GeminiConfigPayload(BaseModel):
    api_key: str | None = None
    model: str | None = None


@router.get("/gemini")
def get_gemini_config():
    settings = get_settings()
    return {
        "configured": bool(settings.gemini_api_key),
        "model": settings.gemini_model,
        "key_preview": "set" if settings.gemini_api_key else "missing",
    }


@router.post("/gemini")
def save_gemini_config_route(payload: GeminiConfigPayload):
    settings = save_gemini_config(payload.api_key, payload.model)
    return {
        "configured": bool(settings.gemini_api_key),
        "model": settings.gemini_model,
        "key_preview": "set" if settings.gemini_api_key else "missing",
    }
