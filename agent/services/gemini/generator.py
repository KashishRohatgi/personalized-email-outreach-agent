from agent.services.gemini.client import GeminiClient
from agent.services.gemini.models import GenerationInput
from agent.services.gemini.prompts import build_prompt
from agent.services.gemini.validator import validate_generated_email
from agent.validators import GeneratedEmail


class GeminiGenerator:
    def __init__(self, client: GeminiClient):
        self.client = client

    def generate(self, data: GenerationInput) -> tuple[GeneratedEmail, str]:
        if not self.client.live:
            output = self._mock_response(data)
            generated, _ = validate_generated_email(
                data.recipient["email"], output, data.research
            )
            return generated, "mock"
        output = self.client.generate_json(build_prompt(data))
        generated, _ = validate_generated_email(
            data.recipient["email"], output, data.research
        )
        return generated, "gemini"

    @staticmethod
    def _mock_response(data: GenerationInput) -> dict:
        name = data.recipient.get("name") or "there"
        objective = data.campaign.get("objective") or "connect"
        summary = data.research.get("professional_summary")
        points = data.research.get("relevant_points") or []
        detail = summary or (points[0] if points else None)
        opening = f"I came across your work{(' on ' + detail) if detail else ''}."
        warning = "MOCK_GENERATION: GEMINI_API_KEY is not configured; live Gemini was not called."
        if not detail:
            warning += " Research was unavailable, so personalization is limited."
        return {
            "subject": f"{objective}: a quick introduction",
            "body": f"Hi {name},\n\n{opening} I am reaching out regarding {objective}. "
            "Would you be open to a brief conversation next week?\n\nBest,\n"
            + (data.campaign.get("sender_info") or "") ,
            "personalization_score": 60 if detail else 25,
            "warnings": [warning],
        }
