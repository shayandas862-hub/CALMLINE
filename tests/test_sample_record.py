"""v4 phase 2 · task 3 — reading the KB's three `III.4` sample records.

The seed book is not typed out; it is parsed from the corpus, through phase 1's
parser. These chunks are the ones deliberately withheld from the retrieval index
(AD-CL-035) precisely so they can be facts here instead of citable rules there.

Their format is one line of backtick-quoted `key: value` pairs separated by ` · `.
"""

import pytest

from src.records.sample_record import (
    SampleRecordError,
    load_sample_records,
    parse_fields,
    parse_money,
)


@pytest.fixture(scope="module")
def records():
    return load_sample_records("data/kb")


# ── the field grammar ────────────────────────────────────────────────────
def test_parse_fields_splits_backticked_pairs():
    text = "`policy_no: LP-20419876` · `status: in force` · `bank_last4: 4471`."
    assert parse_fields(text) == {
        "policy_no": "LP-20419876", "status": "in force", "bank_last4": "4471"}


def test_parse_fields_keeps_colons_inside_a_value():
    text = "`recent: 2026-05-20 switch 10% WP→Managed; 2026-04-02 valuation issued`."
    assert parse_fields(text)["recent"].startswith("2026-05-20 switch")


def test_parse_fields_refuses_a_line_with_no_pairs():
    # Silence here would mean an empty policy record, which must never happen.
    with pytest.raises(SampleRecordError):
        parse_fields("just some prose with no backticked pairs")


def test_parse_money_reads_pounds_into_integer_pence():
    assert parse_money("£400,000") == 40_000_000
    assert parse_money("£212.40/month, DD, next collection 01-08-2026") == 21_240
    assert parse_money("£46,210") == 4_621_000


def test_parse_money_raises_on_a_value_with_no_amount():
    with pytest.raises(SampleRecordError):
        parse_money("none")


# ── the three records are found and keyed ────────────────────────────────
def test_all_three_sample_records_load(records):
    assert set(records) == {"01-WOL:III.4", "02-BOND:III.4", "03-PEN:III.4"}


def test_sample_records_are_the_withheld_chunks(records):
    # Every one of them is excluded from the retrieval index by design.
    assert all(not r.chunk.embed for r in records.values())


def test_the_lifelong_protection_record_parses_its_stated_fields(records):
    fields = records["01-WOL:III.4"].fields
    assert fields["policy_no"] == "LP-20419876"
    assert fields["holder"] == "Theta Meridian 12"
    assert fields["dob"] == "1954-02-11"
    assert fields["sum_assured"] == "£400,000"
    assert fields["start_date"] == "2016-05-01"
    assert fields["bank_last4"] == "4471"


def test_the_bond_record_parses_its_stated_fields(records):
    fields = records["02-BOND:III.4"].fields
    assert fields["policy_no"] == "HB-40582213"
    assert "£120,000 on 2019-03-01" in fields["invested"]
    assert fields["current_value"] == "£151,240"
    assert "£36,000 of £42,000" in fields["withdrawals"]


def test_the_pension_record_parses_its_stated_fields(records):
    fields = records["03-PEN:III.4"].fields
    assert fields["policy_no"] == "RA-77103428"
    assert fields["member"] == "Kappa Quasar 58"
    assert fields["scottish_taxpayer"] == "yes (S-code)"
    assert fields["fund_value"] == "£212,400"
    assert fields["target_retirement_age"] == "60"


# ── the parse is keyed off metadata, never off a filename ────────────────
def test_loading_from_a_directory_with_no_sample_records_raises(tmp_path):
    with pytest.raises(SampleRecordError):
        load_sample_records(str(tmp_path))
