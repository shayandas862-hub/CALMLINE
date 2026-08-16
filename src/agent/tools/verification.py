"""The identity gate, held a second time — inside the tool layer.

The disclosure endpoints already refuse an unverified read (D-CL-052). This is
the layer beneath them: a record tool reached by any other route — a future
endpoint, a background job, a model that found a way to call it — refuses on its
own account rather than trusting that something upstream checked.

Three properties are deliberate:

  * **The guard wraps the binding, not the function.** ``src/casework/assembly.py``
    calls ``lookup_policy_record`` directly and is not part of this phase, so the
    record functions keep their signatures. The requirement is added where the
    tool is bound for the agent, which is also the only place that has a gate and
    an interaction to check against.
  * **The interaction and the policy must both agree.** ``verification_id`` is
    sequential (``VR-000000001``), so validating the id on its own would let one
    caller's live verification unlock another caller's request for the same
    policy. The lookup goes through ``(cn_ref, policy_no)`` first and only then
    matches the id, which makes a guessed or borrowed id worthless.
  * **The refusal says nothing.** It does not name which check failed and does
    not reveal whether the policy exists — `07-RUNBOOK:4.1`, the same rule the
    cannot-verify route follows.

The wrapper publishes a real ``__signature__`` rather than hiding behind
``**kwargs``, so ``src/agent/tools/schemas.py`` derives a schema that tells the
model to supply ``verification_id``. A guard the model cannot see is a guard it
cannot satisfy.
"""

from __future__ import annotations

import inspect
from typing import Any, Callable

_REFUSAL = (
    "no live verification for this policy on this interaction — verify the "
    "caller first (05-OPS:2.4)"
)


class VerificationRequired(RuntimeError):
    """Raised when a record tool is called without a live verification."""


def verified(fn: Callable[..., Any], *, gate: Any,
             cn_ref: str) -> Callable[..., Any]:
    """Wrap a record-reading tool so it refuses without a live verification.

    ``cn_ref`` is session state and is bound here, never taken from the model:
    a caller who could name their own interaction could name someone else's.
    """

    def _guarded(**kwargs: Any) -> Any:
        verification_id = kwargs.pop("verification_id", "")
        record = gate.active_record(cn_ref, kwargs.get("policy_no", ""))
        if record is None or record.verification_id != verification_id:
            raise VerificationRequired(_REFUSAL)
        return fn(**kwargs)

    _guarded.__name__ = getattr(fn, "__name__", "guarded_tool")
    _guarded.__doc__ = getattr(fn, "__doc__", None)
    _guarded.__signature__ = _with_verification_id(fn)  # type: ignore[attr-defined]
    return _guarded


def _with_verification_id(fn: Callable[..., Any]) -> inspect.Signature:
    """``fn``'s signature plus the ``verification_id`` the guard consumes.

    ``eval_str`` for the same reason ``schemas.py`` needs it: the tool modules
    use ``from __future__ import annotations``, so annotations arrive as strings.
    """
    signature = inspect.signature(fn, eval_str=True)
    parameters = list(signature.parameters.values())
    parameters.append(inspect.Parameter(
        "verification_id", inspect.Parameter.KEYWORD_ONLY, annotation=str))
    return signature.replace(parameters=parameters)
