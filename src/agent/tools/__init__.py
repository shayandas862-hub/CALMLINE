"""The agent's toolbox (v3 phase 2).

A small set of single-job tools the CalmLine agent selects between: reading the
system of record, retrieving a clause from the RAG, running a compliance
pre-check, proposing a money movement (never committing it), and raising a
case. Registered in a `ToolRegistry` and run by name through its dispatcher.
"""
