FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    LLM_PROVIDER=ollama \
    OLLAMA_MODEL=llama3.1:8b \
    OPENAI_MODEL=meta-llama/Llama-3.1-8B-Instruct \
    CHECK_PATH_PATTERN=/tmp/check_{date} \
    OUTPUT_DIR=/tmp/reports \
    REQUEST_TIMEOUT_SECONDS=180

WORKDIR /app

COPY requirements.txt /app/requirements.txt
COPY wheelhouse /app/wheelhouse
RUN test -d /app/wheelhouse && \
    pip install --no-cache-dir --no-index --find-links=/app/wheelhouse -r /app/requirements.txt

COPY app /app/app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
