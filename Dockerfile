# syntax=docker/dockerfile:1
FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_DISABLE_PIP_VERSION_CHECK=1 DATA_DIR=/data THUMB_CACHE=/data/thumbs ASSETS_ROOT=/assets ASSETS_LOCK=/app/assets.lock.json
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends espeak-ng ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --uid 10001 --create-home app && mkdir -p /data/thumbs /assets && chown -R app:app /data /assets
COPY game/requirements.txt ./requirements.txt
RUN --mount=type=secret,id=proxy_ca \
    if [ -f /run/secrets/proxy_ca ]; then export PIP_CERT=/run/secrets/proxy_ca; fi; \
    pip install --no-cache-dir -r requirements.txt
COPY --chown=app:app game/ ./
COPY --chown=app:app assets.lock.json ./assets.lock.json
LABEL org.opencontainers.image.source="https://github.com/TuanPham0411/TH-GoT"
ARG APP_REVISION=development
ENV APP_REVISION=$APP_REVISION
USER app
EXPOSE 5000
HEALTHCHECK --interval=15s --timeout=5s --start-period=30m --retries=4 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5000/healthz',timeout=3)"
ENTRYPOINT ["python", "/app/assets.py", "run", "--"]
CMD ["gunicorn","--bind","0.0.0.0:5000","--workers","1","--threads","4","--preload","--no-control-socket","--timeout","45","app:app"]
