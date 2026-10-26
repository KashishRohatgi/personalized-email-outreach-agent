from datetime import datetime

from pydantic import (
    AnyHttpUrl,
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)

CLASSIFICATION_MAX_LENGTH = 255
URL_MAX_LENGTH = 512
NAME_MAX_LENGTH = 255


def _strip_not_blank(value: str, field_name: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError(f"{field_name} must not be blank")
    return value


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ProfileCreate(BaseModel):
    name: str = Field(min_length=1, max_length=NAME_MAX_LENGTH)
    email: EmailStr | None = None
    profile_url: AnyHttpUrl | None = None
    source: str | None = Field(default=None, max_length=255)
    role: str | None = Field(default=None, max_length=NAME_MAX_LENGTH)
    company: str | None = Field(default=None, max_length=NAME_MAX_LENGTH)
    classification: str | None = Field(default=None, max_length=CLASSIFICATION_MAX_LENGTH)
    relevance_score: float | None = Field(default=None, ge=0, le=100)
    professional_summary: str | None = None
    relevant_points: list[str] | None = None
    research_status: str | None = Field(default=None, max_length=64)

    @field_validator("name", "classification")
    @classmethod
    def _name_not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return _strip_not_blank(value, cls.__name__)


class ProfileRead(ORMModel):
    id: int
    name: str
    email: str | None = None
    profile_url: str | None = None
    source: str | None = None
    role: str | None = None
    company: str | None = None
    classification: str | None = None
    relevance_score: float | None = None
    professional_summary: str | None = None
    relevant_points: list[str] | None = None
    research_status: str | None = None
    created_at: datetime
    updated_at: datetime


class ContactCreate(BaseModel):
    name: str = Field(min_length=1, max_length=NAME_MAX_LENGTH)
    email: EmailStr
    role: str | None = Field(default=None, max_length=NAME_MAX_LENGTH)
    company: str | None = Field(default=None, max_length=NAME_MAX_LENGTH)
    context: str | None = None
    notes: str | None = None
    public_url: AnyHttpUrl | None = None
    profile_id: int | None = Field(default=None, ge=1)

    @field_validator("name")
    @classmethod
    def _name_not_blank(cls, value: str) -> str:
        return _strip_not_blank(value, cls.__name__)


class ContactUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=NAME_MAX_LENGTH)
    email: EmailStr | None = None
    role: str | None = Field(default=None, max_length=NAME_MAX_LENGTH)
    company: str | None = Field(default=None, max_length=NAME_MAX_LENGTH)
    context: str | None = None
    notes: str | None = None
    public_url: AnyHttpUrl | None = None
    profile_id: int | None = Field(default=None, ge=1)


class ContactRead(ORMModel):
    id: int
    name: str
    email: str
    role: str | None = None
    company: str | None = None
    context: str | None = None
    notes: str | None = None
    public_url: str | None = None
    profile_id: int | None = None
    created_at: datetime
    updated_at: datetime


class CampaignCreate(BaseModel):
    name: str = Field(min_length=1, max_length=NAME_MAX_LENGTH)
    objective: str | None = None
    sender_info: str | None = None
    tone: str | None = None
    instructions: str | None = None
    status: str | None = Field(default="DRAFT", max_length=64)

    @field_validator("name")
    @classmethod
    def _name_not_blank(cls, value: str) -> str:
        return _strip_not_blank(value, cls.__name__)


class CampaignRead(ORMModel):
    id: int
    name: str
    objective: str | None = None
    sender_info: str | None = None
    tone: str | None = None
    instructions: str | None = None
    status: str
    created_at: datetime
    updated_at: datetime


class CampaignStatusRead(BaseModel):
    campaign_id: int
    total_profiles: int
    relevant_profiles: int
    emails_generated: int
    waiting_for_approval: int
    approved: int
    rejected: int
    drafts_created: int
    drafts_verified: int
    failed: int
    current_campaign_state: str


class EmailCreate(BaseModel):
    contact_id: int = Field(ge=1)
    campaign_id: int = Field(ge=1)
    recipient: EmailStr
    subject: str = Field(default="", max_length=512)
    body: str = Field(min_length=1)
    personalization_score: float | None = Field(default=None, ge=0, le=100)
    warnings: list[str] | None = None
    status: str | None = Field(default="DRAFT", max_length=64)

    @field_validator("body")
    @classmethod
    def _body_not_blank(cls, value: str) -> str:
        return _strip_not_blank(value, cls.__name__)


class EmailRead(ORMModel):
    id: int
    contact_id: int
    campaign_id: int
    recipient: str
    subject: str
    body: str
    personalization_score: float | None = None
    warnings: list[str] | None = None
    status: str
    created_at: datetime
    updated_at: datetime


class EmailUpdate(BaseModel):
    subject: str | None = Field(default=None, max_length=512)
    body: str | None = Field(default=None)

    @field_validator("subject", "body")
    @classmethod
    def _editable_text_not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return _strip_not_blank(value, "email text")

    @model_validator(mode="after")
    def _requires_editable_field(self):
        if self.subject is None and self.body is None:
            raise ValueError("subject or body is required")
        return self


class ReviewDecision(BaseModel):
    reason: str | None = Field(default=None, max_length=2000)

    @field_validator("reason")
    @classmethod
    def _reason_not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return _strip_not_blank(value, "reason")


class GeneratedEmail(BaseModel):
    """The only shape accepted from a Gemini provider."""

    subject: str = Field(min_length=1, max_length=512)
    body: str = Field(min_length=1)
    personalization_score: int = Field(ge=0, le=100)
    warnings: list[str] = Field(default_factory=list)

    @field_validator("subject", "body")
    @classmethod
    def _generated_text_not_blank(cls, value: str) -> str:
        return _strip_not_blank(value, "generated text")


class SearchJobCreate(BaseModel):
    classification: str = Field(min_length=1, max_length=CLASSIFICATION_MAX_LENGTH)
    search_query: str = Field(min_length=1)
    source_urls: list[AnyHttpUrl] = Field(default_factory=list)

    @field_validator("classification", "search_query")
    @classmethod
    def _required_not_blank(cls, value: str) -> str:
        return _strip_not_blank(value, cls.__name__)


class SearchJobRead(ORMModel):
    id: int
    classification: str
    search_query: str
    source_urls: list[str] | None = None
    status: str
    profiles_found: int
    profiles_relevant: int
    created_at: datetime
    completed_at: datetime | None = None


class ActivityRead(ORMModel):
    id: int
    action: str
    details: dict | list | str | None = None
    timestamp: datetime
