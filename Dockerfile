# Minimal, works anywhere
FROM python:3.11-slim

WORKDIR /app

# Install deps first for better build caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY . .

# Default port used by sales_ai.server
ENV PORT=5000
EXPOSE 5000

# Start the server (no extra process manager needed)
CMD ["python", "-m", "sales_ai.server"]
