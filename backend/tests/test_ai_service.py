from types import SimpleNamespace


def test_create_chat_completion_monkeypatched(monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "AI_PROVIDER", "openai")
    fake_resp = {"id": "fake", "choices": [{"message": {"role": "assistant", "content": "Hello from fake"}}]}

    # Monkeypatch the openai.ChatCompletion.create function to avoid network calls
    monkeypatch.setattr("openai.ChatCompletion.create", lambda **kwargs: fake_resp)

    from app.services.ai_service import create_chat_completion

    res = create_chat_completion([{"role": "user", "content": "hi"}])
    assert res is fake_resp
