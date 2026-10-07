"""AI provider abstraction for AI-RMMS.

Keeps model calls behind a small interface so the rest of the application
does not depend on a specific vendor SDK. Gemini is the default provider.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import get_settings


@dataclass(frozen=True)
class AIGenerationResult:
    text: str
    model: str
    provider: str


class AIProviderError(Exception):
    """Raised when the AI provider cannot produce a usable response."""


def generate_text(
    prompt: str,
    *,
    system_instruction: str = "You are the AI-RMMS evidence-based assistant.",
) -> AIGenerationResult | None:
    """Generate text from the configured AI provider.

    Returns None when the provider is not configured or the call fails.
    Callers should fall back to deterministic / evidence-only behaviour.
    """
    settings = get_settings()
    if not settings.gemini_api_key:
        return None

    try:
        from google import genai

        client = genai.Client(api_key=settings.gemini_api_key)
        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
            config={"system_instruction": system_instruction},
        )
        text = (response.text or "").strip()
        if not text:
            return None
        return AIGenerationResult(
            text=text,
            model=settings.gemini_model,
            provider="gemini",
        )
    except Exception:
        return None
