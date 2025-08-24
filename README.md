# SalesCrewPipeline

<p align="center">
  <img src="sales-pipeline.png" alt="SalesCrewPipeline diagram" width="760">
</p>

CLI app that analyzes a `sales.csv` with a 3-step CrewAI pipeline:

1) **Validator** → turns your question into a compact JSON instruction  
2) **Data Analyst** → runs the instruction against the CSV  
3) **Business Analyst Insights** → summarizes the result

---

## Requirements

- **Docker** (Docker Desktop on Windows/macOS, or Docker Engine on Linux)
- **Docker Compose v2**
- **Internet access**
- **OpenAI API key**
- Your dataset at `./data/sales.csv`

Python dependencies are baked into the image (for reference):
- `python-dotenv >= 1.0`
- `pandas >= 2.2`
- `crewai >= 0.35`
- `openai`
- `pydantic`

---

## Setup

1. **Place your dataset**
   ```bash
   mkdir -p data
   # Put your CSV here
   # data/sales.csv
   ```

2. **Create your .env**
   ```env
   OPENAI_API_KEY=sk-...            # required
   SALES_CSV=/data/sales.csv        # path inside the container (matches the volume in compose)
   ```

---

## Run with Docker Compose

```bash
docker compose build
docker compose run --rm app
```

You should see

```bash
🤖 CrewAI Sales Data Analyzer
Ask a question about the dataset:
>
```
Try:

- which product sold the most

- which location had the highest sales
