"""Trace persistence and the five KB metrics.

One record per agent query, shaped by `06-RAGOPS:4.1`, plus the gate events that
make gate-bypass auditable. Everything the ops screen shows is a fold over what
is stored here — no metric computes from anything else, so a number on the board
can always be reproduced from the store that produced it.
"""
