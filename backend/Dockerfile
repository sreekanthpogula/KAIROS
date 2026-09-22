# Build context is the repo root (see docker-compose.yml). The ontology
# YAML lives inside backend/app/ontology_data/ (not a sibling directory) so
# it's always part of this image regardless of build context — see
# app/core/config.py for why.
FROM python:3.11-slim

WORKDIR /app

COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend backend
COPY data/samples data/samples

WORKDIR /app/backend
ENV PYTHONPATH=/app/backend

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
