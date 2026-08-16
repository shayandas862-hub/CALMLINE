"""The record-reading tools over the RecordStore.

Sum assured and premium moved off `Policy` onto the LP cover component, so the
lookup surfaces them only for a product that has them.
"""

from functools import partial

from src.agent.tools.record_tools import get_transaction_history, lookup_policy_record
from src.agent.tools.registry import Tool, ToolRegistry
from src.records.models import gbp
from src.records.seed import build_seed_book

# Injected, never the wall clock — late enough that every seeded movement counts.
AS_AT = "2026-04-12"


def test_lookup_returns_holder_policy_and_current_value():
    book = build_seed_book()
    out = lookup_policy_record(book, "LP-20419876")
    assert out["found"] is True
    assert out["holder"]["name"] == "Theta Meridian 12"
    assert out["holder"]["party_id"] == "PH-0001"
    assert out["policy"]["product"] == "lifelong_protection"
    assert out["current_value_pence"] == gbp(46_210)
    assert out["current_value"] == "£46,210.00"


def test_lookup_surfaces_cover_detail_for_a_product_that_has_it():
    out = lookup_policy_record(build_seed_book(), "LP-20419876")
    assert out["policy"]["sum_assured"] == "£400,000.00"
    assert out["policy"]["premium"] == "£212.40"
    assert out["policy"]["can_pay_cash_out"] is True      # unit-linked


def test_lookup_omits_cover_detail_for_a_product_without_it():
    # A pension has no sum assured; the lookup must not invent one.
    out = lookup_policy_record(build_seed_book(), "RA-77103428")
    assert "sum_assured" not in out["policy"]
    assert out["policy"]["can_pay_cash_out"] is False     # no benefit route


def test_lookup_unknown_policy_returns_not_found():
    out = lookup_policy_record(build_seed_book(), "LP-00000000")
    assert out["found"] is False
    assert out["policy_no"] == "LP-00000000"


def test_history_returns_the_ordered_ledger():
    book = build_seed_book()
    out = get_transaction_history(book, "LP-20419876", AS_AT)
    assert out["found"] is True
    kinds = [e["kind"] for e in out["entries"]]
    balances = [e["balance_after_pence"] for e in out["entries"]]
    assert kinds == ["opening"]
    assert balances == [gbp(46_210)]


def test_history_unknown_policy_returns_not_found():
    out = get_transaction_history(build_seed_book(), "LP-00000000", AS_AT)
    assert out["found"] is False


# --- the ledger is answered as at a date, never undated -------------------
#
# The tool used to take no date at all and return the whole ledger. Phase 4's
# live demo asked what a policy was worth in April and got a history running
# past it — a dated question answered with undated data. A phase about recording
# what happened must not begin by faithfully recording a wrong answer.

def test_history_is_bounded_by_as_at():
    # HB-40582213's credit adjustment lands 2026-04-02. Asked as at 15 March, it
    # has not happened yet and must not appear.
    out = get_transaction_history(build_seed_book(), "HB-40582213", "2026-03-15")
    assert out["as_at"] == "2026-03-15"
    assert [e["seq"] for e in out["entries"]] == [1, 2, 3, 4, 5, 6, 7]
    assert "credit_adjustment" not in [e["kind"] for e in out["entries"]]


def test_history_value_is_the_value_as_at_that_date():
    # £120,000 opening less six £6,000 withdrawals — not the £151,240 the policy
    # is worth once April's adjustment is counted.
    out = get_transaction_history(build_seed_book(), "HB-40582213", "2026-03-15")
    assert out["value_pence"] == gbp(84_000)
    assert out["value"] == "£84,000.00"


def test_history_before_the_policy_opened_is_empty_not_current():
    # The sharpest form of the old bug: a date before anything happened must
    # produce an empty ledger and a zero value, never today's figures.
    out = get_transaction_history(build_seed_book(), "HB-40582213", "2019-01-01")
    assert out["entries"] == []
    assert out["value_pence"] == 0


def test_record_tools_work_through_the_registry_with_the_store_bound():
    book = build_seed_book()
    reg = ToolRegistry()
    reg.register(Tool("lookup_policy_record", "look up a policy",
                      partial(lookup_policy_record, book)))
    out = reg.dispatch("lookup_policy_record", {"policy_no": "LP-20419876"})
    assert out["current_value_pence"] == gbp(46_210)
