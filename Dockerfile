FROM python:3.11-slim
WORKDIR /app

# deps first (cache-friendly)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# copy app (including sales.csv at repo root)
COPY . .

# default CSV path inside the image; can be overridden by .env
ENV SALES_CSV=/data/sales.csv
ENV PYTHONUNBUFFERED=1

# run the CLI
CMD ["python", "-c", "from sales_ai.crewapp import main; main()"]