from sqlalchemy import inspect


def test_database_creation(db_session):
    inspector = inspect(db_session.bind)
    tables = set(inspector.get_table_names())
    expected = {
        "profiles",
        "search_jobs",
        "contacts",
        "campaigns",
        "email_records",
        "activity_logs",
        "workflows",
    }
    assert expected <= tables


def test_database_schema_columns(db_session):
    inspector = inspect(db_session.bind)
    profile_cols = {c["name"] for c in inspector.get_columns("profiles")}
    assert {
        "id",
        "name",
        "email",
        "profile_url",
        "source",
        "role",
        "company",
        "classification",
        "relevance_score",
        "professional_summary",
        "relevant_points",
        "research_status",
        "created_at",
        "updated_at",
    } <= profile_cols

    search_cols = {c["name"] for c in inspector.get_columns("search_jobs")}
    assert {
        "classification",
        "search_query",
        "source_urls",
        "status",
        "profiles_found",
        "profiles_relevant",
        "completed_at",
    } <= search_cols

    contact_cols = {c["name"] for c in inspector.get_columns("contacts")}
    assert "profile_id" in contact_cols

    email_cols = {c["name"] for c in inspector.get_columns("email_records")}
    assert {
        "contact_id",
        "campaign_id",
        "recipient",
        "subject",
        "body",
        "personalization_score",
        "warnings",
        "status",
    } <= email_cols