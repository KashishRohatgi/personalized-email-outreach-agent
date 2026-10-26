import json
from typing import Any


class GeminiError(RuntimeError):
    pass


class GeminiClient:
    """Small adapter that keeps the Google SDK out of application code and tests."""

    def __init__(self, api_key: str | None, model: str, sdk_client: Any = None):
        self.api_key = api_key
        self.model = model
        self._sdk_client = sdk_client

    @property
    def live(self) -> bool:
        return bool(self.api_key)

    def generate_json(self, prompt: str) -> dict:
        if not self.api_key:
            raise GeminiError("GEMINI_API_KEY is not configured")
        try:
            if self._sdk_client is None:
                from google import genai
                self._sdk_client = genai.Client(api_key=self.api_key)
            response = self._sdk_client.models.generate_content(
                model=self.model,
                contents=prompt,
                config={"response_mime_type": "application/json"},
            )
            text = getattr(response, "text", None)
            if not text:
                raise GeminiError("Gemini returned an empty response")
            value = json.loads(text)
            if not isinstance(value, dict):
                raise GeminiError("Gemini response was not a JSON object")
            return value
        except GeminiError:
            raise
        except Exception as exc:
            raise GeminiError(f"Gemini request failed: {type(exc).__name__}") from exc
