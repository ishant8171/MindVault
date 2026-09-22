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
import httpx
import openai

from app.core.config import settings


class AIProviderNotConfiguredError(Exception):
    """Raised when the AI provider API key is missing or not configured."""
    pass


def _init_openai() -> None:
    if settings.OPENAI_API_KEY:
        openai.api_key = settings.OPENAI_API_KEY


def _create_gemini_completion(
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    max_tokens: int = 256,
    temperature: float = 0.7,
) -> Dict[str, Any]:
    if not settings.GEMINI_API_KEY:
        raise AIProviderNotConfiguredError(
            "AI provider is not configured: GEMINI_API_KEY is not set. "
            "Please configure GEMINI_API_KEY in the environment or .env file."
        )

    model_name = model or settings.GEMINI_MODEL
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={settings.GEMINI_API_KEY}"

    system_parts = []
    contents = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role == "system":
            system_parts.append({"text": content})
        else:
            gemini_role = "model" if role == "assistant" else "user"
            contents.append({
                "role": gemini_role,
                "parts": [{"text": content}]
            })

    if not contents:
        contents.append({"role": "user", "parts": [{"text": "Hello"}]})

    payload: Dict[str, Any] = {
        "contents": contents,
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
        },
    }
    if system_parts:
        payload["systemInstruction"] = {"parts": system_parts}

    try:
        resp = httpx.post(url, json=payload, timeout=60.0)
        if resp.status_code != 200:
            raise RuntimeError(f"Gemini API returned status {resp.status_code}: {resp.text}")
        data = resp.json()
        text = ""
        candidates = data.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            if parts:
                text = parts[0].get("text", "")
        return {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": text,
                    }
                }
            ],
            "raw": data,
        }
    except Exception as exc:
        raise RuntimeError(f"AI provider call failed: {exc}") from exc


def create_chat_completion(
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    max_tokens: int = 256,
    temperature: float = 0.7,
) -> Dict[str, Any]:
    """Create a chat completion using the configured provider.

    Returns the normalized provider response dict. Callers may inspect or
    normalize the result as needed.
    """
    if settings.AI_PROVIDER == "gemini":
        return _create_gemini_completion(
            messages=messages,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
        )
    elif settings.AI_PROVIDER == "openai":
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
    else:
        raise NotImplementedError(f"AI provider '{settings.AI_PROVIDER}' is not supported")


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
        AIProviderNotConfiguredError if API key is empty/unset.
    """
    if settings.AI_PROVIDER == "gemini":
        if not settings.GEMINI_API_KEY:
            raise AIProviderNotConfiguredError(
                "AI provider is not configured: GEMINI_API_KEY is not set. "
                "Please configure GEMINI_API_KEY in the environment or .env file."
            )
    else:
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
