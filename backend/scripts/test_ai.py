"""Manual script to exercise the AI service locally.

Usage:
    python scripts/test_ai.py

Make sure `OPENAI_API_KEY` is set in your environment or in `backend/.env`.
"""
from app.services import ai_service


def main():
    print("Model:", ai_service.__dict__.get('__name__'))
    resp = ai_service.generate_text("Say hello and identify yourself.")
    # Print provider's text content if available
    try:
        print(resp["choices"][0]["message"]["content"])  # provider-specific
    except Exception:
        print(resp)


if __name__ == "__main__":
    main()
