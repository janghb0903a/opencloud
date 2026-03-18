FROM python:3.11-slim

WORKDIR /app

# Offline install: all dependency wheels must exist under ./wheels.
COPY --chown=65534:65534 requirements.txt /app/requirements.txt
COPY --chown=65534:65534 wheels /wheels
RUN pip install --no-cache-dir --no-index --find-links=/wheels -r /app/requirements.txt \
    && rm -rf /wheels

COPY --chown=65534:65534 server.py /app/server.py
RUN chmod 0755 /app && chmod 0644 /app/server.py

USER 65534:65534
EXPOSE 9189

ENTRYPOINT ["python", "/app/server.py"]
