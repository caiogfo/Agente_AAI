"""Thin, provider-flexible LLM interface.

The delivered configuration uses Anthropic Claude (claude-opus-4-8, the most
powerful Opus, validated with the account key and wired in .env.example); OpenAI
(gpt-4o-mini) is also supported and takes over when OPENAI_API_KEY is set. The key
is read from the environment, never hardcoded. A local .env file (gitignored)
loads automatically if present.

The rest of the engine is fully functional with NO key (deterministic fallback in
narrate.py); the LLM only adds narrative polish on top of the grounded facts.
"""
from __future__ import annotations

import os
from pathlib import Path

_ENV = Path(__file__).resolve().parent.parent / ".env"


def _load_dotenv() -> None:
    """Minimal .env loader (KEY=VALUE per line), no external dependency."""
    if not _ENV.exists():
        return
    for line in _ENV.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_dotenv()

OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-opus-4-8")


def provider() -> str | None:
    if os.environ.get("OPENAI_API_KEY"):
        return "openai"
    if os.environ.get("ANTHROPIC_API_KEY"):
        return "anthropic"
    return None


def have_key() -> bool:
    return provider() is not None


def complete(system: str, user: str, *, model: str | None = None,
             max_tokens: int = 1600, temperature: float = 0.2) -> str:
    """Single-turn completion. Raises if no key / SDK error (caller falls back)."""
    prov = provider()
    if prov == "openai":
        from openai import OpenAI

        client = OpenAI()
        resp = client.chat.completions.create(
            model=model or OPENAI_MODEL,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": user}],
        )
        return resp.choices[0].message.content or ""

    if prov == "anthropic":
        import anthropic

        client = anthropic.Anthropic()
        mdl = model or ANTHROPIC_MODEL
        kwargs = dict(model=mdl, max_tokens=max_tokens, system=system,
                      messages=[{"role": "user", "content": user}])
        # Newer Anthropic models (e.g. Opus 4.8) deprecate `temperature`; only send
        # it to models that still accept it, so the call works across model versions.
        if "opus-4-8" not in mdl:
            kwargs["temperature"] = temperature
        msg = client.messages.create(**kwargs)
        return "".join(b.text for b in msg.content if b.type == "text")

    raise RuntimeError("No LLM API key set (OPENAI_API_KEY or ANTHROPIC_API_KEY).")
