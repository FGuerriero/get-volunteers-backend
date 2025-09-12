# Copyright (c) 2025 Fernando Guerriero Cardoso da Silva.
# Created Date: Mon Sep 08 2025
# SPDX-License-Identifier: MIT

# Build stage
FROM python:3.11-slim as builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM python:3.11-slim

WORKDIR /app

RUN useradd --create-home --shell /bin/bash app

COPY --from=builder --chown=app:app /root/.local /home/app/.local

COPY --chown=app:app . .

USER app

ENV PATH=/home/app/.local/bin:$PATH

EXPOSE 8000

CMD ["uvicorn", "app.app:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]