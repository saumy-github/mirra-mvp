# syntax=docker/dockerfile:1

# Build context is the repo root (see docker-compose.yml). Python deps for
# the whole repo live in one root requirements.txt by convention (avatar/
# ingestion pipelines and this backend share one venv/requirements file) -
# but this image installs only website/backend/requirements-docker.txt, a
# curated subset of it. website/backend/src never imports the CLO/ML stack
# (torch, transformers, opencv, ...) further down in the root file - that's
# only used by clo_avatar_generation/clo_vto/product_ingestion, none of
# which are COPYed into this image - so installing the full file here was
# pure waste (~9GB image, ~10min rebuild on any requirements.txt touch).
FROM python:3.12.10-slim AS base

WORKDIR /app

COPY website/backend/requirements-docker.txt ./requirements-docker.txt
# Cache mount (not --no-cache-dir): requirements-docker.txt changing
# invalidates this layer, but the pip wheel/download cache below persists
# across builds regardless, so only new/changed package versions actually
# hit the network. See .agent/website-launch/07-step0-worker-queue.md's
# execution log for the rebuild this was added to fix.
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements-docker.txt

COPY website/backend ./website/backend

WORKDIR /app/website/backend

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
