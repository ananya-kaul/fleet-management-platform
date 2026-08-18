# Fleet Management API

FastAPI backend for the Fleet Management Platform.
See the [root README](../README.md) for the full project documentation.

## Quick start

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
alembic upgrade head
python -m app.seed          # optional demo data
uvicorn app.main:app --reload
```

Interactive API docs: http://127.0.0.1:8000/docs
