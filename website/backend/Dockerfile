# Build context is the repo root (see docker-compose.yml) because Python deps
# for this whole repo live in one root requirements.txt by convention -
# avatar/ingestion pipelines and this backend share one venv/requirements file.
FROM python:3.12.10-slim AS base

WORKDIR /app

COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY website/backend ./website/backend

WORKDIR /app/website/backend

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
