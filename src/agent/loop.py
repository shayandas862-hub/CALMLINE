"""The SDK contract and the primitives both agent paths share.

**There is one loop now: `src/agent/console_loop.py`** — N tools from the
registry, a `ConsoleReply`, and the identity gate held inside the tool layer.
Phase 6's task 4 pointed the eval runner at it too, so an eval run and a console
answer are the same shape by construction (D-CL-084).

`run_agent` used to live here: a second loop driving one `policy_lookup` tool
and validating into a `CallVerdict` or a `ComplianceChecklist`. With the runner
moved, nothing reached it but its own tests, and nothing graded either shape.
All three were removed rather than left in the tree looking like a supported
path (D-CL-089).

What stays is what the console loop, the provenance backfill and the agent route
all import: the typed failure, the step and token ceilings, and the final-text
reader. Any API failure or malformed output raises ``AgentError`` — the agent
NEVER fabricates an answer.

SDK contract: adaptive thinking (`thinking={"type": "adaptive"}` is the only
on-mode) where the model supports it, depth via `output_config.effort`,
structured final output via `output_config.format`, and `strict` tool schemas.
No sampling params (`temperature`/`top_p`/`top_k`) and no `budget_tokens` — all
four are rejected. **Which models accept thinking is asked, never assumed:**
``request_shape`` in ``console_loop.py`` is the one place that decides, because
a model predating adaptive thinking fails outright when sent it.
"""

from __future__ import annotations

from typing import Any

from src.config import Config

# Read off the config class's committed default rather than restated here, so
# there is one source for the model id and no literal to drift (D-CL-024,
# D-CL-053 contradiction 5). Reading `model_fields` does not instantiate Config,
# so this costs nothing and needs no secrets. The console path does not use it
# at all — `run_console_agent` requires the caller to pass a model.
DEFAULT_MODEL = Config.model_fields["ANTHROPIC_MODEL"].default
# Measured at the live smoke: the target two-part query used 4 steps in
# isolation and exhausted 6 through the console, where the corpus is wider.
# 8 leaves headroom without letting a runaway loop bill indefinitely.
_MAX_STEPS = 8
_MAX_TOKENS = 4096


class AgentError(RuntimeError):
    """Raised on any API failure or malformed output — never a fabricated answer."""


def _final_text(response: Any) -> str:
    parts = [getattr(b, "text", "") for b in response.content
             if getattr(b, "type", None) == "text"]
    return "".join(parts).strip()
