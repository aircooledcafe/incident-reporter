FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_ARTIFACTS_ROOT=/data/artifacts \
    DJANGO_STATIC_ROOT=/app/backend/staticfiles

WORKDIR /app/backend

# Install system dependencies required by Pillow
RUN apt-get update && apt-get install -y --no-install-recommends \
    libjpeg62-turbo-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app/backend/
RUN sed -i 's/\r$//' /app/backend/entrypoint.sh && \
    chmod +x /app/backend/entrypoint.sh && \
    mkdir -p /data/artifacts /app/backend/staticfiles && \
    DJANGO_SECRET_KEY="docker-build-collectstatic-placeholder" \
    DJANGO_ARTIFACTS_ROOT="/tmp/build_artifacts" \
    python manage.py collectstatic --noinput && \
    rm -rf /tmp/build_artifacts

VOLUME ["/data/artifacts"]

EXPOSE 8000

ENTRYPOINT ["/app/backend/entrypoint.sh"]
