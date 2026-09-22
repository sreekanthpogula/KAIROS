# Build context is the repo root (see docker-compose.yml) so this image can
# preserve the backend/ontology/data sibling layout that Settings'
# REPO_ROOT-relative defaults (ontology path, upload dir) expect.
FROM python:3.11-slim

WORKDIR /app

COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend backend
COPY ontology ontology
COPY data/samples data/samples

WORKDIR /app/backend
ENV PYTHONPATH=/app/backend

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
