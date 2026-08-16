"""Reading the KB's three `III.4` sample records into structured fields.

The seed book is parsed from the corpus, not typed out — so a change to the KB
shows up as a change to the book rather than as a quiet divergence between the
two. These are the chunks deliberately withheld from the retrieval index
(AD-CL-035): they are facts for the system of record, never citable rules.

Their format is one line of backtick-quoted ``key: value`` pairs separated by
` · `. Anything that will not parse raises — a policy record that silently comes
back half-empty is worse than one that fails loudly.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from src.corpus.kb_parser import parse_kb
from src.records.models import AdviserLoa
from src.records.products import FundHolding

FIELD_RE = re.compile(r"`([^`:]+):\s*([^`]*)`")
MONEY_RE = re.compile(r"£\s*([\d,]+(?:\.\d{1,2})?)")


class SampleRecordError(RuntimeError):
    """Raised when a sample record cannot be read as a policy record."""


@dataclass(frozen=True)
class SampleRecord:
    """One parsed `type=sample_record` chunk."""

    chunk_id: str
    fields: dict[str, str]
    chunk: Any

    def require(self, name: str) -> str:
        """A field the record must carry — missing raises rather than defaults."""
        if name not in self.fields:
            raise SampleRecordError(
                f"{self.chunk_id}: sample record has no {name!r} field "
                f"(has {sorted(self.fields)})"
            )
        return self.fields[name]

    def get(self, name: str, default: str = "") -> str:
        return self.fields.get(name, default)


def parse_fields(text: str) -> dict[str, str]:
    """Split a sample-record line into its ``key: value`` pairs."""
    pairs = FIELD_RE.findall(text)
    if not pairs:
        raise SampleRecordError(
            "sample record carries no backticked `key: value` pairs")
    return {key.strip(): value.strip().rstrip(".") for key, value in pairs}


def parse_money(value: str) -> int:
    """First £ amount in ``value`` as integer pence. `£212.40/month` → 21240."""
    match = MONEY_RE.search(value)
    if match is None:
        raise SampleRecordError(f"no £ amount in {value!r}")
    return int(round(float(match.group(1).replace(",", "")) * 100))


def parse_all_money(value: str) -> list[int]:
    """Every £ amount in ``value``, in order — for "£36,000 of £42,000"."""
    return [int(round(float(raw.replace(",", "")) * 100))
            for raw in MONEY_RE.findall(value)]


def parse_date(value: str) -> str:
    """The first ISO date in ``value``."""
    match = re.search(r"\d{4}-\d{2}-\d{2}", value)
    if match is None:
        raise SampleRecordError(f"no ISO date in {value!r}")
    return match.group(0)


def load_sample_records(kb_dir: str) -> dict[str, SampleRecord]:
    """Parse every `type=sample_record` chunk under ``kb_dir``, keyed by chunk id.

    Selection is by the chunk's own ``type`` metadata, never by filename, so a
    renamed document still seeds the book and a new sample record is picked up
    without editing this module.
    """
    records = {
        chunk.chunk_id: SampleRecord(chunk_id=chunk.chunk_id,
                                     fields=parse_fields(chunk.text), chunk=chunk)
        for chunk in parse_kb(kb_dir) if chunk.type == "sample_record"
    }
    if not records:
        raise SampleRecordError(f"no type=sample_record chunks found under {kb_dir!r}")
    return records


# ── reading a stated field into a model shape ────────────────────────────

def address_and_registered(raw: str) -> "tuple[str, bool]":
    """`14 Lattice Way, Demoford (registered)` → the address, and the flag."""
    registered = "(registered)" in raw
    return re.sub(r"\s*\(registered\)", "", raw).strip(), registered

def adviser_loa_from(raw: str) -> "AdviserLoa | None":
    """`Fairholm Financial Ltd, FRN 512345 (fictional), scope=servicing+information,
    expires 2027-03` → the authority, or nothing when the record says "none"."""
    if raw.strip().lower() == "none":
        return None
    firm = raw.split(",")[0].strip()
    frn = re.search(r"FRN\s*(\d+)", raw)
    scope = re.search(r"scope=([\w+]+)", raw)
    expiry = re.search(r"expires\s*([\d-]+)", raw)
    return AdviserLoa(firm=firm, frn=frn.group(1) if frn else "",
                      scope=tuple(scope.group(1).split("+")) if scope else (),
                      expiry=expiry.group(1) if expiry else "")

def reversed_date(raw: str) -> "str | None":
    """`next collection 01-08-2026` → `2026-08-01`."""
    match = re.search(r"(\d{2})-(\d{2})-(\d{4})", raw)
    return f"{match.group(3)}-{match.group(2)}-{match.group(1)}" if match else None

def funds_from(raw: str) -> "list[FundHolding]":
    """`60% Managed Growth (AMC 0.65%), 40% With-Profits (§3.6)` → fund rows.

    One AMC often covers the whole line, so a fund without its own stated charge
    inherits the line's — recorded rather than defaulted to zero.
    """
    amc_match = re.search(r"AMC\s*([\d.]+)%", raw)
    amc_bp = int(round(float(amc_match.group(1)) * 100)) if amc_match else 0
    funds = []
    for part in re.split(r",(?=\s*\d+%)", raw):
        match = re.match(r"\s*(\d+)%\s*([^(]+)", part)
        if not match:
            continue
        name = match.group(2).strip()
        funds.append(FundHolding(fund_id=f"ALD-{_slug(name)}", fund_name=name,
                                 split_pct=int(match.group(1)), amc_bp=amc_bp,
                                 price_date="2026-07-13"))
    return funds

def _slug(name: str) -> str:
    return "".join(word[0] for word in re.findall(r"[A-Za-z0-9]+", name)).upper()[:6]

def months_before(as_at: str, count: int) -> "list[str]":
    """The first of each of the ``count`` months ending before ``as_at``."""
    year, month = int(as_at[:4]), int(as_at[5:7])
    months = []
    for _ in range(count):
        month -= 1
        if month == 0:
            year, month = year - 1, 12
        months.append(f"{year}-{month:02d}-01")
    return sorted(months)
