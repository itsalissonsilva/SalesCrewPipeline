# syntax=docker/dockerfile:1.7-labs
FROM python:3.11-slim

WORKDIR /app

# Install deps first (cacheable) — use pip cache + prefer wheels
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install --upgrade pip && \
    pip install --prefer-binary -r requirements.txt

# Copy app
COPY . .

ENV PORT=5000
EXPOSE 5000

CMD ["python", "-m", "sales_ai.server"]
