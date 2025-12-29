from __future__ import annotations

import pendulum

from airflow.models.dag import DAG
from airflow.operators.bash import BashOperator

with DAG(
    dag_id="skincare_daily_pipeline",
    schedule="@daily",
    start_date=pendulum.datetime(2023, 1, 1, tz="Asia/Jakarta"),
    catchup=False,
    tags=["skincare", "pipeline"],
    doc_md="""
    ## Skincare Daily Pipeline
    
    This DAG runs the main ETL pipeline for the skincare project.
    It executes the `src/pipeline.py` script.
    """
) as dag:
    run_pipeline = BashOperator(
        task_id="run_main_pipeline",
        # Assuming your project directory is mounted at /opt/airflow in the Airflow container
        # This is a common practice when using the official Airflow Docker Compose setup.
        bash_command="python /opt/airflow/src/pipeline.py",
    )
