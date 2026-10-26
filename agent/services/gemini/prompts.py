import json

from agent.services.gemini.models import GenerationInput


def build_prompt(data: GenerationInput) -> str:
    payload = {
        "recipient": data.recipient,
        "research": data.research,
        "campaign": data.campaign,
    }
    return (
        "Generate one concise professional outreach email as JSON with exactly these "
        "keys: subject, body, personalization_score, warnings. Use only facts in the "
        "provided research. Never infer or invent projects, awards, employment, events, "
        "relationships, meetings, publications, or personal interests. If research is "
        "limited, write a simpler email and include a warning. Avoid generic flattery "
        "and 'I hope this email finds you well'. Include a clear purpose and CTA.\n\n"
        + json.dumps(payload, ensure_ascii=True)
    )
