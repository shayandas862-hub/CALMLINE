"""v4 phase 4 · Task 5 — which agent answered, and saying so.

The console runs offline by default and live when a key is configured. The
choice has to be honest on screen: a keyword answer presented as the real agent
would misrepresent the product in exactly the direction that flatters it.

The key is **injected**, never read through ``load_config()``. `ANTHROPIC_API_KEY`
is in `config.REQUIRED`, so the loader raises naming *every* missing variable —
a console with no `.env` would die on `SUPABASE_URL` before it ever reached the
key check (D-CL-053 contradiction 4). Selection therefore takes the value it
needs and stays a pure decision, which also makes it deterministic to test.
"""

import pytest

from src.web.console.agent_select import AgentChoice, select_agent

MODEL = "claude-sonnet-5"


def test_a_configured_key_selects_the_live_loop():
    # Act
    choice = select_agent(api_key="sk-ant-something", model=MODEL)

    # Assert
    assert choice.live is True
    assert choice.mode == "live"
    assert choice.model == MODEL


def test_no_key_falls_back_to_the_keyword_path():
    # Act
    choice = select_agent(api_key=None, model=MODEL)

    # Assert
    assert choice.live is False
    assert choice.mode == "keyword"


def test_an_empty_key_is_not_a_key():
    # An exported-but-blank variable is the most common way to have "a key"
    # that cannot authenticate anything.
    # Act / Assert
    assert select_agent(api_key="", model=MODEL).live is False
    assert select_agent(api_key="   ", model=MODEL).live is False


def test_the_keyword_path_reports_no_model():
    # Naming a model that never ran would be the pretence this exists to stop.
    # Act
    choice = select_agent(api_key=None, model=MODEL)

    # Assert
    assert choice.model is None


def test_both_paths_say_why_in_words_a_handler_can_read():
    # Act
    live = select_agent(api_key="sk-ant-x", model=MODEL)
    offline = select_agent(api_key=None, model=MODEL)

    # Assert
    assert live.reason and offline.reason
    assert live.reason != offline.reason
    assert "key" in offline.reason.lower()


def test_the_model_reported_is_the_one_passed_in():
    # Nothing here decides the model; it comes from configuration.
    # Act
    choice = select_agent(api_key="sk-ant-x", model="claude-opus-5")

    # Assert
    assert choice.model == "claude-opus-5"


def test_selecting_never_reads_configuration_and_so_never_raises():
    # The whole point of contradiction 4: a console with no .env still boots.
    # Act
    choice = select_agent(api_key=None, model=MODEL)

    # Assert
    assert isinstance(choice, AgentChoice)


def test_the_keyword_model_is_demoted_not_deleted():
    # D-CL-020 — the zero-key fallback stays reachable.
    # Act
    from src.web.console.offline_agent import KeywordModel

    # Assert
    assert KeywordModel(policy_no="LP-20419876") is not None


def test_a_choice_cannot_be_edited_after_it_is_made():
    # Act
    choice = select_agent(api_key="sk-ant-x", model=MODEL)

    # Assert
    with pytest.raises(Exception):
        choice.mode = "keyword"  # type: ignore[misc]
