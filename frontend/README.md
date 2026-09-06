MindVault frontend (Phase 10)

Quick start:

1. Install dependencies

```bash
cd frontend
npm install
```

2. Start dev server (ensure backend is running on `VITE_API_BASE_URL`)

```bash
npm run dev
```

Notes:
- Configure `VITE_API_BASE_URL` in `.env` or use default `http://localhost:8000`.
- JWTs are stored in `localStorage` by the Auth provider.
