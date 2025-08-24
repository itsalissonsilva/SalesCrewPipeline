# SalesCrewPipeline

<p align="center">
  <img src="sales-pipeline.png" alt="SalesCrewPipeline diagram" width="760">
</p>

CLI app that analyzes a `sales.csv` with a 3-step CrewAI pipeline:

1) **Validator** → turns your question into a compact JSON instruction  
2) **Data Analyst** → runs the instruction against the CSV  
3) **Business Insights** → summarizes the result

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
- `openai >= 1`
- `pydantic >= 2`

---

## Setup

1. **Place your dataset**
   ```bash
   mkdir -p data
   # Put your CSV here
   # data/sales.csv

2. **Create your .env**

OPENAI_API_KEY=sk-...            # required
SALES_CSV=/data/sales.csv        # path inside the container (matches the volume in compose)


Create compose.yaml (repo root)

services:
  app:
    build: .
    env_file: .env
    stdin_open: true   # keep STDIN open for the CLI
    tty: true          # allocate a TTY
    volumes:
      - ./data:/data:ro


Run with Docker compose

docker compose build
docker compose run --rm app
