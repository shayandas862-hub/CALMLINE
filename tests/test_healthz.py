"""v4 phase 7 · Task 2 — the health endpoint, and what "honest" means in it.

A health check exists so a platform and a human can both ask *is this service
actually working*. Two ways to get that wrong, and this file pins both shut:

* **Reporting a component without looking at it.** "store: ok" that is a
  hard-coded string is worse than no health check, because it is believed. Every
  component here is derived by *doing* the thing — counting policies out of the
  store, counting chunks out of the corpus.
* **Refusing to answer.** A health check behind a login, or one that 500s when a
  component is down, tells the platform to kill a service at exactly the moment
  someone needs to look at it. It answers 200 and says what is wrong in the body.
"""

import pytest
from fastapi.testclient import TestClient

from src.web.console.app import create_console_app
from src.web.console.health_routes import health_report


def client(**over):
    return TestClient(create_console_app(secret="test-secret", **over))


# ── it answers, to anyone, always ──────────────────────────────────────
def test_answers_200_without_a_login():
    """A health check behind an auth wall is a health check nobody can use."""
    response = client().get("/healthz")
    assert response.status_code == 200


def test_reports_all_three_components():
    body = client().get("/healthz").json()
    assert set(body["components"]) == {"config", "store", "corpus"}
    assert body["status"] in ("ok", "degraded")


# ── each component is derived, never asserted ──────────────────────────
def test_the_corpus_count_is_the_real_one():
    from src.web.console.offline_agent import searchable_chunks

    body = client().get("/healthz").json()
    assert body["components"]["corpus"]["clauses"] == len(searchable_chunks())
    assert body["components"]["corpus"]["clauses"] > 0


def test_the_store_count_is_read_out_of_the_store():
    from src.records.seed import build_seed_book

    book = build_seed_book()
    body = client(book=book).get("/healthz").json()
    assert body["components"]["store"]["policies"] == len(book.list_policies())


class BrokenBook:
    def list_policies(self):
        raise RuntimeError("connection refused")


def test_a_store_that_raises_is_reported_down_rather_than_crashing_the_check():
    """The one request that must survive everything else being broken."""
    report = health_report(book=BrokenBook(), corpus_clauses=438, config_ok=True)
    assert report["components"]["store"]["ok"] is False
    assert "connection refused" in report["components"]["store"]["detail"]
    assert report["status"] == "degraded"


# ── config, and the honesty of "not checked" ───────────────────────────
def test_config_is_reported_unchecked_in_development():
    """Development deliberately validates nothing (D-CL-053). Saying 'ok' here
    would be claiming a check that never ran."""
    component = client().get("/healthz").json()["components"]["config"]
    assert component["ok"] is None
    assert "not checked" in component["detail"].lower()


def test_an_unchecked_config_does_not_make_the_service_degraded():
    """Unknown is not broken — a local console is not a sick one."""
    assert client().get("/healthz").json()["status"] == "ok"


def test_a_failed_config_check_is_degraded_but_still_answers():
    report = health_report(book=BrokenBook.__new__(BrokenBook), corpus_clauses=1,
                           config_ok=False)
    assert report["components"]["config"]["ok"] is False
    assert report["status"] == "degraded"


def test_a_passed_config_check_is_reported_as_checked():
    from src.records.seed import build_seed_book

    report = health_report(book=build_seed_book(), corpus_clauses=438, config_ok=True)
    assert report["components"]["config"]["ok"] is True
    assert report["status"] == "ok"


def test_the_console_passes_its_config_state_through():
    body = client(config_ok=True).get("/healthz").json()
    assert body["components"]["config"]["ok"] is True


# ── the status is the worst component, not the average ─────────────────
@pytest.mark.parametrize("config_ok, expected", [(True, "ok"), (False, "degraded")])
def test_one_bad_component_degrades_the_whole_report(config_ok, expected):
    from src.records.seed import build_seed_book

    report = health_report(book=build_seed_book(), corpus_clauses=438,
                           config_ok=config_ok)
    assert report["status"] == expected
