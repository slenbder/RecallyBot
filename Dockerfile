# syntax=docker/dockerfile:1
FROM python:3.12-slim

# tzdata so zoneinfo("Europe/Moscow") resolves for the human-readable dates;
# the slim image doesn't ship the zone database.
RUN apt-get update \
    && apt-get install -y --no-install-recommends tzdata \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Install deps first (better layer caching): copy only what pip needs to resolve.
COPY pyproject.toml ./
COPY bot ./bot
RUN pip install --no-cache-dir .

# DB lives on a mounted volume, not in the image (see compose).
ENV DB_PATH=/data/reviews.db

CMD ["python", "-m", "bot.main"]
