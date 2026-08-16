"""Back-office casework (v3 phase 3).

The work model for the reviewer's desk: a `Case` with a priority and an SLA, a
`CaseQueue` that ranks the work, assembly of the "whole story" case detail, and
the human-gated approval that commits a proposed movement to the ledger. This is
a NEW module, separate from the older `workflow/cases.py`, which is left intact.
"""
