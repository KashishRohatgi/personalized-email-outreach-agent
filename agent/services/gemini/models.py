from dataclasses import dataclass


@dataclass(frozen=True)
class GenerationInput:
    recipient: dict
    research: dict
    campaign: dict
