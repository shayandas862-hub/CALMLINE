"""The Supabase client wrapper: correct wiring (unit) + reachability (integration).

The unit test proves get_client passes the configured URL and service key to
the Supabase factory, with no network. The integration test actually reaches
the three tables and is skipped unless live credentials are in the environment
(so it never runs in CI).
"""

import pytest

from src.config import MissingConfigError, load_config
from src.db import client as db_client

FAKE_CONFIG = load_config(
    env={
        "SUPABASE_URL": "https://demo.supabase.co",
        "SUPABASE_SERVICE_KEY": "service-key-value",
        "ANTHROPIC_API_KEY": "anthropic-demo-key",
        "OPENAI_API_KEY": "openai-demo-key",
        "COHERE_API_KEY": "cohere-demo-key",
        "DATABASE_URL": "postgresql://demo:demo@db.demo.supabase.co:5432/postgres",
    }
)


def test_get_client_wires_url_and_key(monkeypatch):
    # Arrange — capture what the factory is called with
    calls = {}

    def fake_create_client(url, key):
        calls["url"] = url
        calls["key"] = key
        return "fake-client"

    monkeypatch.setattr(db_client, "create_client", fake_create_client)

    # Act
    result = db_client.get_client(FAKE_CONFIG)

    # Assert
    assert result == "fake-client"
    assert calls["url"] == "https://demo.supabase.co"
    assert calls["key"] == "service-key-value"


@pytest.mark.integration
def test_all_four_tables_are_reachable():
    # Arrange — needs the live CalmLine Supabase project; skip otherwise
    try:
        cfg = load_config()
    except MissingConfigError:
        pytest.skip("no live Supabase credentials in environment")

    client = db_client.get_client(cfg)

    # Act / Assert — a select raises if the migration is unapplied. The corpus
    # table is kb_chunks now (v2's policy_clauses retired with data/policies/),
    # and it is keyed by chunk_id rather than a surrogate id.
    client.table("kb_chunks").select("chunk_id").limit(1).execute()
    for table in ("cases", "mock_policy_records", "audit_log"):
        client.table(table).select("id").limit(1).execute()
