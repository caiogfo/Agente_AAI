"""Thin Anthropic Claude interface (provider-isolated).

Reads ANTHROPIC_API_KEY from the environment. The rest of the engine is fully
functional without a key (deterministic fallback in narrate.py); the LLM only
adds the narrative polish on top of the grounded facts.
"""
from __future__ import annotations

import os

# Default model is overridable via env so the key owner can pick what their plan
# supports. Current Claude family IDs: claude-opus-4-8 / claude-sonnet-4-6 / ...
DEFAULT_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")


def have_key() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def complete(system: str, user: str, *, model: str | None = None,
             max_tokens: int = 1600, temperature: float = 0.2) -> str:
    """Single-turn completion. Raises if no key / SDK error (caller falls back)."""
    import anthropic  # imported lazily

    client = anthropic.Anthropic()  # picks up ANTHROPIC_API_KEY
    msg = client.messages.create(
        model=model or DEFAULT_MODEL,
        max_tokens=max_tokens,
        temperature=temperature,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return "".join(block.text for block in msg.content if block.type == "text")
