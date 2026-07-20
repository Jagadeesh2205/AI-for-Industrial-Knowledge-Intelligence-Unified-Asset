FROM python:3.11-slim

WORKDIR /app

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt && \
    python -m spacy download en_core_web_sm

COPY backend /app/backend
COPY data/sample_docs /app/data/sample_docs

ENV LLM_PROVIDER=gemini \
    PORT=8080

EXPOSE 8080

# Cloud Run injects PORT; default 8080
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT}"]
