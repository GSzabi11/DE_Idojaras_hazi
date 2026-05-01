from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta

#Alapbeállítások 
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2026, 3, 29), # múltbéli dátum, hogy azonnal elinduljon
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1, # Ha hiba van, egyszer próbálja újra
    'retry_delay': timedelta(minutes=1),
}

#A DAG definíciója
with DAG(
    'idojaras_pipeline_hazi_feladat',
    default_args=default_args,
    description='Időjárás adat pipeline házi feladat',
    schedule_interval=timedelta(minutes=30),
    catchup=False,
    tags=['homework', 'weather'],
) as dag:
    # Task 1: Extract
    extract_task = BashOperator(
        task_id='extract_data_from_api',
        bash_command='python /opt/airflow/scripts/extract.py', 
    )

    # Task 2: Transform & Load
    transform_load_task = BashOperator(
        task_id='transform_and_load_to_postgres',
        bash_command='python /opt/airflow/scripts/transform.py',
    )

    # Függőségek beállítása
    extract_task >> transform_load_task