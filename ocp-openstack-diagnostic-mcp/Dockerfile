FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
COPY config ./config
COPY runbooks ./runbooks
RUN pip install --no-cache-dir .

USER 65532:65532
EXPOSE 8080
ENTRYPOINT ["ocp-openstack-diagnostic-mcp"]
CMD ["--transport", "http", "--host", "0.0.0.0", "--port", "8080", "--path", "/mcp"]

