"""Trusts, adviser mandates, third-party authorities and bank mandates.

Everything here exists to be **refused** on some policies and allowed on others,
so the counts are the substance rather than the packaging. They come from the
bucket plan, whose governing rule is that every situation the system can refuse
has at least three policies that would trigger it.

Four modules:

- `counts`   — the bucket plan's figures, named and in one place
- `trusts`   — executed and not, registrable and not (`05-OPS:5.8`)
- `mandates` — letters of authority and third-party authorities (`05-OPS:5.1`)
- `banking`  — verification state, holds, and the change history the fraud
  pattern is answered from (`05-OPS:3.4`)
"""

from __future__ import annotations

from world.lifetimes.authorities.banking import (
    allocate_bank_mandates,
    changed_shortly_before,
)
from world.lifetimes.authorities.counts import (
    ATTORNEYS_EPA,
    ATTORNEYS_LPA_REGISTERED,
    ATTORNEYS_LPA_UNREGISTERED,
    ATTORNEYS_TOTAL,
    BANK_ON_HOLD,
    BANK_RECENTLY_CHANGED,
    BANK_UNVERIFIED,
    BANK_VERIFIED,
    BOOK_SIZE,
    DEPUTIES,
    MANDATES_ACTIVE,
    MANDATES_EXPIRED,
    MANDATES_REVOKED,
    MANDATES_TOTAL,
    MANDATES_UNVERIFIED,
    PERSONAL_REPRESENTATIVES,
    RECENT_CHANGE_WINDOW_DAYS,
    SCOPE_INFORMATION_SERVICING,
    SCOPE_PLUS_SWITCHES,
    SCOPE_PLUS_WITHDRAWALS,
    TRUSTS_EXECUTED_AND_REGISTERED,
    TRUSTS_NEVER_EXECUTED,
    TRUSTS_REGISTRABLE_UNREGISTERED,
    TRUSTS_TOTAL,
)
from world.lifetimes.authorities.mandates import (
    allocate_mandates,
    allocate_third_party_authorities,
)
from world.lifetimes.authorities.trusts import allocate_trusts, is_registrable

__all__ = [
    "ATTORNEYS_EPA", "ATTORNEYS_LPA_REGISTERED", "ATTORNEYS_LPA_UNREGISTERED",
    "ATTORNEYS_TOTAL", "BANK_ON_HOLD", "BANK_RECENTLY_CHANGED",
    "BANK_UNVERIFIED", "BANK_VERIFIED", "BOOK_SIZE", "DEPUTIES",
    "MANDATES_ACTIVE", "MANDATES_EXPIRED", "MANDATES_REVOKED",
    "MANDATES_TOTAL", "MANDATES_UNVERIFIED", "PERSONAL_REPRESENTATIVES",
    "RECENT_CHANGE_WINDOW_DAYS", "SCOPE_INFORMATION_SERVICING",
    "SCOPE_PLUS_SWITCHES", "SCOPE_PLUS_WITHDRAWALS",
    "TRUSTS_EXECUTED_AND_REGISTERED", "TRUSTS_NEVER_EXECUTED",
    "TRUSTS_REGISTRABLE_UNREGISTERED", "TRUSTS_TOTAL",
    "allocate_bank_mandates", "allocate_mandates",
    "allocate_third_party_authorities", "allocate_trusts",
    "changed_shortly_before", "is_registrable",
]
