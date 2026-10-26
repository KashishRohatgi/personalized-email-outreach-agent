from email_validator import EmailNotValidError, validate_email

from agent.validators import GeneratedEmail


class EmailValidationError(ValueError):
    pass


def validate_generated_email(
    recipient: str, output: dict, research: dict
) -> tuple[GeneratedEmail, list[str]]:
    try:
        validate_email(recipient, check_deliverability=False)
    except EmailNotValidError as exc:
        raise EmailValidationError("Invalid recipient email") from exc

    try:
        generated = GeneratedEmail.model_validate(output)
    except Exception as exc:
        raise EmailValidationError("Gemini output did not match the required schema") from exc

    warnings = list(generated.warnings)
    research_text = " ".join(
        str(value) for value in research.values() if value not in (None, "", [], {})
    ).lower()
    if not research_text.strip():
        warnings.append("Research was unavailable; personalization is limited.")

    unsupported_phrases = (
        "saw your presentation",
        "we met at",
        "our previous conversation",
        "mutual connection",
        "your award",
        "your publication",
    )
    body_lower = generated.body.lower()
    unsupported = [phrase for phrase in unsupported_phrases if phrase in body_lower and phrase not in research_text]
    if unsupported:
        raise EmailValidationError("Generated email contains unsupported research claims")

    if generated.personalization_score < 40:
        warnings.append("Personalization score is low.")
    return generated.model_copy(update={"warnings": list(dict.fromkeys(warnings))}), warnings
