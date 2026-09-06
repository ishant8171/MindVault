Local development and tests for the MindVault backend.

Setup (optional, if not using Docker):

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# edit .env to set JWT_SECRET_KEY
```

Run the app locally:

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Run tests:

```bash
pytest -q
```

The API docs are available at `http://127.0.0.1:8000/docs` when the app is running.
