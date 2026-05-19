FROM registry.access.redhat.com/ubi9/python-311:latest

WORKDIR /app

USER 0
RUN dnf install -y iputils \
    && dnf clean all
RUN mkdir -p /app /data \
    && chown -R 1001:0 /app /data

COPY --chown=1001:0 requirements.txt /app/requirements.txt
COPY --chown=1001:0 wheels /wheels
RUN if find /wheels -maxdepth 1 -type f \( -name '*.whl' -o -name '*.tar.gz' -o -name '*.zip' \) | grep -q .; then \
      echo "Installing Python dependencies from /wheels"; \
      python -m pip install --no-cache-dir --no-index --find-links=/wheels -r /app/requirements.txt; \
    else \
      echo "No offline packages found in /wheels; falling back to online pip install"; \
      python -m pip install --no-cache-dir -r /app/requirements.txt; \
    fi \
    && rm -rf /wheels

COPY --chown=1001:0 app /app

EXPOSE 9088

USER 1001

ENTRYPOINT ["python", "/app/openstack_vm_recovery.py"]
