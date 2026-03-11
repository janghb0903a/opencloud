FROM python:3.11-bookworm@sha256:1f5ef5d90111a26e41154cdb565670a919c5c804d911c85f7bb604e344dbb5d6

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

ARG APT_MIRROR=deb.debian.org
ARG APT_SCHEME=https
ARG OFFLINE_PIP=false
ARG OFFLINE_APT=false

COPY debs /opt/debs
RUN set -eux; \
    if [ "${OFFLINE_APT}" = "true" ]; then \
      ls /opt/debs/*.deb >/dev/null 2>&1 || (echo "No .deb files found in /opt/debs"; exit 1); \
      apt-get install -y --no-install-recommends /opt/debs/*.deb; \
    else \
      sed -i "s|http://deb.debian.org|${APT_SCHEME}://${APT_MIRROR}|g" /etc/apt/sources.list.d/debian.sources; \
      sed -i "s|http://security.debian.org|${APT_SCHEME}://${APT_MIRROR}|g" /etc/apt/sources.list.d/debian.sources || true; \
      for i in 1 2 3 4 5; do \
        apt-get -o Acquire::Retries=3 update && break; \
        echo "apt-get update retry: ${i}"; \
        sleep 3; \
      done; \
      apt-get install -y --no-install-recommends skopeo ca-certificates; \
      rm -rf /var/lib/apt/lists/*; \
    fi

WORKDIR /app

COPY requirements.txt /app/requirements.txt
COPY wheelhouse /opt/wheelhouse
RUN set -eux; \
    if [ "${OFFLINE_PIP}" = "true" ]; then \
      pip install --no-cache-dir --no-index --find-links=/opt/wheelhouse -r /app/requirements.txt; \
    else \
      pip install --no-cache-dir -r /app/requirements.txt; \
    fi

COPY app /app/app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
