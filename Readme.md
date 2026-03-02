# airflow-weather

A beginner-friendly Apache Airflow pipeline that fetches hourly weather data for Copenhagen from the [Open-Meteo API](https://open-meteo.com/) and stores it in PostgreSQL — all running locally via Docker Compose.

Built as a hands-on introduction to core Airflow concepts: DAGs, PythonOperators, XComs, task dependencies, and scheduling.

---

## Project Structure

```
airflow-weather/
├── docker-compose.yml       # Airflow + PostgreSQL services
├── .env                     # AIRFLOW_UID (generated on setup)
├── dags/
│   └── weather_dag.py       # The pipeline DAG
├── logs/                    # Airflow task logs (auto-generated)
└── plugins/                 # Custom operators (empty for now)
```

---

## Pipeline Overview

The DAG `weather_copenhagen` runs **daily at 6am** and executes three tasks in sequence:

```
extract_weather  →  load_to_postgres  →  validate_rows
```

| Task | What it does |
|---|---|
| `extract_weather` | Calls Open-Meteo API for 24h hourly forecast (Copenhagen) |
| `load_to_postgres` | Creates table if needed, inserts hourly rows |
| `validate_rows` | Counts rows and asserts the table is not empty |

### Data collected per hour
- `timestamp` — hour of the forecast
- `temperature` — °C at 2m height
- `precipitation` — mm
- `windspeed` — km/h at 10m height

---

## Tech Stack

| Tool | Role |
|---|---|
| Apache Airflow 2.9.0 | Orchestration & scheduling |
| PostgreSQL 15 | Data storage |
| Docker Compose | Local infrastructure |
| Open-Meteo API | Weather data source (free, no API key) |
| Python / psycopg2 | Data extraction and loading |

---

## Prerequisites

- Docker Desktop installed and running
- Docker Compose v2+

---

## Setup & Run

**1. Clone or create the project folder:**
```bash
mkdir -p ~/code/airflow-weather/{dags,logs,plugins}
cd ~/code/airflow-weather
```

**2. Generate the environment file:**
```bash
echo "AIRFLOW_UID=$(id -u)" > .env
```

**3. Initialize the Airflow database (run once):**
```bash
docker compose up airflow-init
```

**4. Start all services:**
```bash
docker compose up -d airflow-webserver airflow-scheduler postgres
```

**5. Verify all containers are running:**
```bash
docker compose ps
```

You should see 3 containers with status `running` and PostgreSQL marked `healthy`.

**6. Open the Airflow UI:**
```
http://localhost:8080
```
Login: `admin / admin`

**7. Trigger the DAG manually:**

Click the ▶ play button next to `weather_copenhagen` → **Trigger DAG**.

---

## Verify Data in PostgreSQL

```bash
# Row count and date range
docker exec airflow-weather-postgres-1 psql -U airflow -d airflow \
  -c "SELECT COUNT(*), MIN(timestamp), MAX(timestamp) FROM weather_copenhagen;"

# Sample rows
docker exec airflow-weather-postgres-1 psql -U airflow -d airflow \
  -c "SELECT timestamp, temperature, precipitation, windspeed FROM weather_copenhagen LIMIT 5;"
```

---

## Key Airflow Concepts Demonstrated

| Concept | Where |
|---|---|
| **DAG** | `weather_copenhagen` definition in `weather_dag.py` |
| **PythonOperator** | All 3 tasks wrap plain Python functions |
| **XCom** | `extract_weather` pushes data; `load_to_postgres` pulls it |
| **Task dependencies** | `extract >> load >> validate` |
| **Retries** | `retries=2`, `retry_delay=2min` on all tasks |
| **Scheduling** | `0 6 * * *` — every day at 6am |

---

## Stopping the Project

```bash
docker compose down          # Stop containers, keep data
docker compose down -v       # Stop containers and delete all data
```

---

## Next Steps

- Add a `BranchPythonOperator` to skip loading if the API returns no data
- Use Airflow **Connections** to store PostgreSQL credentials securely
- Add a second city DAG (e.g. Tirana, Rome)
- Integrate **dbt** as a transformation task after loading
- Add a daily summary table with average temperature per day
