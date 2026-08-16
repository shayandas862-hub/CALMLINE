"""The bucket plan's counts, in one place and named.

Every figure here comes from the world's bucket plan, whose governing rule is
that **every situation the system can refuse has at least three policies that
would trigger it** — three rather than one, so a
demonstration never rests on a single row and tidying one away cannot silently
delete a capability.

They are constants rather than arguments because the allocators must meet them
*exactly*; a count passed in is a count that can be passed in wrong.
"""

from __future__ import annotations

# §4 — trusts, an overlay over the 200 rather than a partition.
TRUSTS_TOTAL = 32
TRUSTS_EXECUTED_AND_REGISTERED = 20
TRUSTS_NEVER_EXECUTED = 6
TRUSTS_REGISTRABLE_UNREGISTERED = 6

# §5 — adviser mandates, spread across the twelve firms.
MANDATES_TOTAL = 46
MANDATES_ACTIVE = 30
MANDATES_EXPIRED = 8
MANDATES_UNVERIFIED = 5
MANDATES_REVOKED = 3
SCOPE_INFORMATION_SERVICING = 26
SCOPE_PLUS_SWITCHES = 14
SCOPE_PLUS_WITHDRAWALS = 6

# §6 — powers of attorney, deputies, personal representatives.
ATTORNEYS_LPA_REGISTERED = 8
ATTORNEYS_EPA = 3
ATTORNEYS_LPA_UNREGISTERED = 3
ATTORNEYS_TOTAL = 14
DEPUTIES = 5
PERSONAL_REPRESENTATIVES = 8

# §7 — bank details, a partition of all 200.
BANK_VERIFIED = 152
BANK_UNVERIFIED = 18
BANK_ON_HOLD = 12
BANK_RECENTLY_CHANGED = 18
RECENT_CHANGE_WINDOW_DAYS = 90

BOOK_SIZE = 200
