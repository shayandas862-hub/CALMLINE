"""Langfuse tracing wrapper.

Usage pattern (context manager):
    tracer = get_tracer()
    trace = tracer.trace("query", input={"q": query}, user_id=user_id)
    with trace.span("retrieval", input={"q": query}) as span:
        results = await search(query)
        span.set_output({"count": len(results)})
    with trace.generation("llm", model="gemini-flash", input=messages) as gen:
        answer = await generate(results)
        gen.set_output(answer, usage={"input": 500, "output": 200})
    trace.set_output({"answer": answer})
    tracer.flush()

When LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY are absent or empty, every
call becomes a no-op so Phase 3 services need no conditional logic.
"""
from __future__ import annotations

from typing import Any

from langfuse import Langfuse

from app.core.config import get_settings


# ---------------------------------------------------------------------------
# No-op implementations (used when Langfuse is not configured)
# ---------------------------------------------------------------------------

class _NoopSpan:
    def set_output(self, output: Any, *, usage: dict | None = None) -> None:
        pass

    def set_error(self, error: Exception) -> None:
        pass

    def __enter__(self) -> "_NoopSpan":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        return False


class _NoopTrace:
    def span(self, name: str, *, input: Any = None, metadata: dict | None = None) -> _NoopSpan:
        return _NoopSpan()

    def generation(
        self,
        name: str,
        *,
        model: str,
        input: Any = None,
        metadata: dict | None = None,
        model_params: dict | None = None,
    ) -> _NoopSpan:
        return _NoopSpan()

    def set_output(self, output: Any) -> None:
        pass


# ---------------------------------------------------------------------------
# Live implementations (used when Langfuse is configured)
# ---------------------------------------------------------------------------

class _LiveSpan:
    """Wraps a Langfuse StatefulSpanClient or StatefulGenerationClient."""

    def __init__(self, span: Any) -> None:
        self._span = span
        self._ended = False

    def set_output(self, output: Any, *, usage: dict | None = None) -> None:
        kw: dict[str, Any] = {"output": output}
        if usage is not None:
            kw["usage"] = usage
        self._span.end(**kw)
        self._ended = True

    def set_error(self, error: Exception) -> None:
        self._span.update(level="ERROR", status_message=str(error))
        self._span.end()
        self._ended = True

    def __enter__(self) -> "_LiveSpan":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        if exc_val is not None and not self._ended:
            self.set_error(exc_val)
        elif not self._ended:
            self._span.end()
            self._ended = True
        return False


class _LiveTrace:
    """Wraps a Langfuse StatefulTraceClient."""

    def __init__(self, trace: Any, client: Any) -> None:
        self._trace = trace
        self._client = client

    def span(self, name: str, *, input: Any = None, metadata: dict | None = None) -> _LiveSpan:
        s = self._trace.span(name=name, input=input, metadata=metadata or {})
        return _LiveSpan(s)

    def generation(
        self,
        name: str,
        *,
        model: str,
        input: Any = None,
        metadata: dict | None = None,
        model_params: dict | None = None,
    ) -> _LiveSpan:
        g = self._trace.generation(
            name=name,
            model=model,
            input=input,
            metadata=metadata or {},
            model_parameters=model_params or {},
        )
        return _LiveSpan(g)

    def set_output(self, output: Any) -> None:
        self._trace.update(output=output)

    def flush(self) -> None:
        self._client.flush()


# ---------------------------------------------------------------------------
# Public tracer
# ---------------------------------------------------------------------------

class LangfuseTracer:
    """Thin wrapper around the Langfuse client with graceful no-op fallback."""

    def __init__(self) -> None:
        settings = get_settings()
        self._client: Any = None
        if settings.LANGFUSE_PUBLIC_KEY and settings.LANGFUSE_SECRET_KEY:
            self._client = Langfuse(
                public_key=settings.LANGFUSE_PUBLIC_KEY,
                secret_key=settings.LANGFUSE_SECRET_KEY,
                host=settings.LANGFUSE_HOST,
            )

    @property
    def enabled(self) -> bool:
        return self._client is not None

    def trace(
        self,
        name: str,
        *,
        input: Any = None,
        metadata: dict | None = None,
        user_id: str | None = None,
    ) -> _LiveTrace | _NoopTrace:
        if self._client is None:
            return _NoopTrace()
        t = self._client.trace(
            name=name,
            input=input,
            metadata=metadata or {},
            user_id=user_id,
        )
        return _LiveTrace(t, self._client)

    def flush(self) -> None:
        if self._client is not None:
            self._client.flush()


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_tracer: LangfuseTracer | None = None


def get_tracer() -> LangfuseTracer:
    global _tracer
    if _tracer is None:
        _tracer = LangfuseTracer()
    return _tracer


def reset_tracer() -> None:
    """Reset the cached singleton. Used by tests only."""
    global _tracer
    _tracer = None
