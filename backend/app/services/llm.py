"""Thin wrapper around the Claude API. Returns None when the LLM is unavailable so callers can fall back."""
import logging

import anthropic

from app.config import settings

log = logging.getLogger(__name__)
_client: anthropic.Anthropic | None = None

# Models that accept the server-side refusal fallback ("default" routing)
_FALLBACK_MODELS = {"claude-opus-5-5", "claude-opus-5", "claude-fable-5-1", "claude-sonnet-5-5"}


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=settings.anthropic_api_key, timeout=90.0, max_retries=2)
    return _client


def complete(system: str, prompt: str, max_tokens: int = 4000) -> str | None:
    if not settings.llm_enabled:
        return None
    kwargs: dict = {
        "model": settings.claude_model,
        "max_tokens": max_tokens,
        "system": system,
        "messages": [{"role": "user", "content": prompt}],
        "output_config": {"effort": settings.claude_effort},
    }
    if settings.claude_model in _FALLBACK_MODELS:
        kwargs["betas"] = ["server-side-fallback-2026-07-01"]
        kwargs["fallbacks"] = "default"
    try:
        response = _get_client().beta.messages.create(**kwargs)
    except anthropic.AuthenticationError:
        log.error("Claude API key is invalid - check ANTHROPIC_API_KEY")
        return None
    except anthropic.RateLimitError:
        log.warning("Claude API rate limited")
        return None
    except anthropic.APIStatusError as exc:
        log.error("Claude API error %s: %s", exc.status_code, exc.message)
        return None
    except anthropic.APIConnectionError:
        log.error("Could not reach the Claude API")
        return None

    if response.stop_reason == "refusal":
        log.warning("Claude declined the request")
        return None
    text = "".join(block.text for block in response.content if block.type == "text").strip()
    return text or None
