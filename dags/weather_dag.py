import requests
import psycopg2
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator

POSTGRES_CONN = {
    "host": "postgres",
    "database": "airflow",
    "user": "airflow",
    "password": "airflow",
    "port": 5432
}

LATITUDE = 55.6761
LONGITUDE = 12.5683


def extract_weather(**context):
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={LATITUDE}&longitude={LONGITUDE}"
        f"&hourly=temperature_2m,precipitation,windspeed_10m"
        f"&forecast_days=1"
    )
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()
    context['ti'].xcom_push(key='weather_data', value=data)
    print(f"Extracted {len(data['hourly']['time'])} hourly records")


def load_to_postgres(**context):
    data = context['ti'].xcom_pull(key='weather_data', task_ids='extract_weather')
    hourly = data['hourly']
    conn = psycopg2.connect(**POSTGRES_CONN)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS weather_copenhagen (
            id            SERIAL PRIMARY KEY,
            timestamp     TIMESTAMP NOT NULL,
            temperature   FLOAT,
            precipitation FLOAT,
            windspeed     FLOAT,
            loaded_at     TIMESTAMP DEFAULT NOW()
        )
    """)
    for ts, temp, precip, wind in zip(
        hourly['time'],
        hourly['temperature_2m'],
        hourly['precipitation'],
        hourly['windspeed_10m']
    ):
        cur.execute("""
            INSERT INTO weather_copenhagen (timestamp, temperature, precipitation, windspeed)
            VALUES (%s, %s, %s, %s)
        """, (ts, temp, precip, wind))
    conn.commit()
    cur.close()
    conn.close()
    print(f"Loaded {len(hourly['time'])} rows into weather_copenhagen")


def validate_rows(**context):
    conn = psycopg2.connect(**POSTGRES_CONN)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM weather_copenhagen")
    count = cur.fetchone()[0]
    cur.close()
    conn.close()
    print(f"Total rows in weather_copenhagen: {count}")
    assert count > 0, "Validation failed: table is empty!"


default_args = {
    "owner": "alket",
    "retries": 2,
    "retry_delay": timedelta(minutes=2),
    "email_on_failure": False
}

with DAG(
    dag_id="weather_copenhagen",
    description="Daily weather pipeline for Copenhagen via Open-Meteo",
    start_date=datetime(2024, 1, 1),
    schedule_interval="0 6 * * *",
    catchup=False,
    default_args=default_args,
    tags=["weather", "learning"]
) as dag:

    extract = PythonOperator(
        task_id="extract_weather",
        python_callable=extract_weather
    )

    load = PythonOperator(
        task_id="load_to_postgres",
        python_callable=load_to_postgres
    )

    validate = PythonOperator(
        task_id="validate_rows",
        python_callable=validate_rows
    )

    extract >> load >> validate
