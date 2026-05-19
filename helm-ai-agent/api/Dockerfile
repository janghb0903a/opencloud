FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV LLM_BACKEND=bedrock \
    AWS_REGION=us-east-1 \
    BEDROCK_MODEL_ID=anthropic.claude-3-haiku-20240307-v1:0
EXPOSE 8000
CMD ["uvicorn","app:app","--host","0.0.0.0","--port","8000"]
