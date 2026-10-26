import pytest

from agent.services.gemini.client import GeminiClient, GeminiError
from agent.services.gemini.generator import GeminiGenerator
from agent.services.gemini.models import GenerationInput
from agent.services.gemini.validator import EmailValidationError, validate_generated_email


def _input(research=None, objective="Research collaboration"):
    return GenerationInput(
        recipient={"name": "Ada Lovelace", "email": "ada@example.com"},
        research=research or {"professional_summary": "AI researcher in computer vision"},
        campaign={"objective": objective, "sender_info": "Grace"},
    )


def test_mock_generation_is_structured_and_explicit():
    result, provider = GeminiGenerator(GeminiClient(None, "gemini-2.5-flash")).generate(_input())
    assert provider == "mock"
    assert result.subject
    assert result.body
    assert result.personalization_score in range(101)
    assert any("MOCK_GENERATION" in warning for warning in result.warnings)


def test_missing_key_is_reported_by_live_client():
    with pytest.raises(GeminiError, match="GEMINI_API_KEY"):
        GeminiClient(None, "gemini-2.5-flash").generate_json("prompt")


def test_live_client_parses_structured_sdk_response():
    class Response:
        text = '{"subject":"Hello","body":"Let us connect.","personalization_score":70,"warnings":[]}'

    class Models:
        def generate_content(self, **kwargs):
            return Response()

    class SDK:
        models = Models()

    output = GeminiClient("provided-at-runtime", "gemini-2.5-flash", SDK()).generate_json("prompt")
    assert output["personalization_score"] == 70


def test_live_client_wraps_provider_failure_without_exposing_credentials():
    class Models:
        def generate_content(self, **kwargs):
            raise TimeoutError("provider timeout")

    class SDK:
        models = Models()

    with pytest.raises(GeminiError, match="Gemini request failed"):
        GeminiClient("secret-value", "gemini-2.5-flash", SDK()).generate_json("prompt")


def test_malformed_output_is_blocked():
    with pytest.raises(EmailValidationError):
        validate_generated_email("ada@example.com", {"subject": "Only subject"}, {})


def test_invalid_recipient_is_blocked():
    with pytest.raises(EmailValidationError, match="recipient"):
        validate_generated_email(
            "not-an-email",
            {"subject": "Hello", "body": "Please connect.", "personalization_score": 50},
            {},
        )


def test_unsupported_claim_is_blocked():
    with pytest.raises(EmailValidationError, match="unsupported"):
        validate_generated_email(
            "ada@example.com",
            {
                "subject": "Hello",
                "body": "I saw your presentation at the conference.",
                "personalization_score": 50,
            },
            {"professional_summary": "AI researcher"},
        )


def test_limited_research_adds_warning():
    result, warnings = validate_generated_email(
        "ada@example.com",
        {"subject": "Hello", "body": "Would you be open to connecting?", "personalization_score": 25},
        {},
    )
    assert result.warnings
    assert warnings
