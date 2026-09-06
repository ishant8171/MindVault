"""
AI provider abstraction layer.

This module is the ONLY module anywhere in the codebase allowed to import the
OpenAI SDK or know the value of AI_PROVIDER.

Primary function for Phase 4+:
    generate_response(system_prompt: str, user_message: str) -> str

Exceptions:
    AIProviderNotConfiguredError: Raised when OPENAI_API_KEY is not configured,
    preventing silent failures or fabricated responses.
"""

from typing import Any, Dict, List, Optional
import openai

from app.core.config import settings


class AIProviderNotConfiguredError(Exception):
    """Raised when the AI provider API key is missing or not configured."""
    pass


def _init_openai() -> None:
    if settings.OPENAI_API_KEY:
        openai.api_key = settings.OPENAI_API_KEY


def create_chat_completion(
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    max_tokens: int = 256,
    temperature: float = 0.7,
) -> Dict[str, Any]:
    """Create a chat completion using the configured provider.

    Returns the raw provider response dict. Callers may inspect or
    normalize the result as needed.
    """
    if settings.AI_PROVIDER != "openai":
        raise NotImplementedError(f"AI provider '{settings.AI_PROVIDER}' is not supported")

    _init_openai()

    try:
        resp = openai.ChatCompletion.create(
            model=model or settings.OPENAI_MODEL,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return resp
    except Exception as exc:
        raise RuntimeError(f"AI provider call failed: {exc}") from exc


def generate_text(
    prompt: str, system_message: Optional[str] = None, model: Optional[str] = None, **kwargs
) -> Dict[str, Any]:
    """Convenience wrapper: sends a single-user prompt and returns raw provider response."""
    messages: List[Dict[str, str]] = []
    if system_message:
        messages.append({"role": "system", "content": system_message})
    messages.append({"role": "user", "content": prompt})
    return create_chat_completion(messages, model=model, **kwargs)


def generate_response(
    system_prompt: str,
    user_message: str,
    model: Optional[str] = None,
    **kwargs,
) -> str:
    """
    Primary interface for ContextAssemblyService.
    Generates a natural language response given a system prompt and user message.

    Raises:
        AIProviderNotConfiguredError if OPENAI_API_KEY is empty/unset.
    """
    if not settings.OPENAI_API_KEY:
        raise AIProviderNotConfiguredError(
            "AI provider is not configured: OPENAI_API_KEY is not set. "
            "Please configure OPENAI_API_KEY in the environment or .env file."
        )

    resp = generate_text(prompt=user_message, system_message=system_prompt, model=model, **kwargs)
    try:
        return resp["choices"][0]["message"]["content"]
    except Exception:
        return str(resp)
