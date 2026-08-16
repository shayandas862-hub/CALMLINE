"""Playing a policy from the day it started to the world's birth date.

The engine is `timeline.py`; what it would not accept lands in `report.py`. The
per-product mechanics — what a bond, a pension and a whole-of-life policy each
propose and each refuse — plug into the engine's rule seam and live in their own
packages beside this one.

**Every movement is offered to the rulebook before it is accepted.** The world
cannot be born breaking its own rules, because the code that would refuse a live
handler is the code that builds it.
"""

from __future__ import annotations

from world.lifetimes.report import Refusal, RefusalReport
from world.lifetimes.timeline import Lifetime, Movement, play

__all__ = ["Lifetime", "Movement", "Refusal", "RefusalReport", "play"]
