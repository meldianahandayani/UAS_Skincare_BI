from __future__ import annotations

import pendulum
from datetime import date
import pandas as pd
from pathlib import Path
import json # for detailed_analysis which is stored as JSON string in silver

from airflow.models.dag import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago

# Make sure src directory is in Python path for imports
# This is typically handled by Docker volume mounts and/or custom Dockerfile
# For Airflow to find these modules, the 'src' directory needs to be accessible
# Example: Adding /opt/airflow/src to PYTHONPATH in custom Dockerfile or entrypoint script

# Import all run functions
# NOTE: These imports assume 'src' is on the PYTHONPATH of the Airflow worker.
# In a Docker setup, you'd typically mount your project's 'src' directory
# to a location like '/opt/airflow/src' and ensure it's added to the PYTHONPATH.
try:
    from src.ingest import inventory, sheets, weather, scrape_ingredients
    from src.transform import build_silver, build_gold
    from src.utils.paths import part_dir # For constructing paths in temporary tasks
except ImportError as e:
    print(f"Failed to import src modules: {e}")
    print("Ensure 'src' directory is in PYTHONPATH or modules are directly accessible.")
    # Define dummy functions for local testing if imports fail outside Airflow environment
    # In a real Airflow deployment, this ImportError should prevent DAG parsing.
    class DummyModule:
        def run(*args, **kwargs):
            print(f"Dummy run called for {e}")
            if 'd' in kwargs and kwargs['d']:
                # Return dummy path based on date for build_silver to read
                return f"/tmp/dummy_output_{kwargs['d'].isoformat()}.csv"
            if 'product_list' in kwargs:
                return pd.DataFrame([{"nama_produk": "Dummy Product", "url": "", "html_path": "", "scraped_date": kwargs['d']}])
            return {}
    inventory = sheets = weather = scrape_ingredients = build_silver = build_gold = DummyModule()
    class DummyPaths:
        def part_dir(*args): return Path("/tmp")
        def ensure_dir(*args): return Path("/tmp")
    part_dir = DummyPaths().part_dir


def _get_execution_date(context) -> date:
    """Helper to get the execution date as a date object."""
    return pendulum.parse(context["ds"]).date()

def _ingest_inventory_task(ti, **context):
    exec_date = _get_execution_date(context)
    result_path = inventory.run(exec_date)
    ti.xcom_push(key="inventory_path", value=result_path)
    return result_path

def _ingest_sheets_task(ti, **context):
    exec_date = _get_execution_date(context)
    result_path = sheets.run(exec_date)
    ti.xcom_push(key="sheets_path", value=result_path)
    return result_path

def _ingest_weather_task(ti, **context):
    exec_date = _get_execution_date(context)
    # Using default lat/lon from src/utils/config.py
    # If dynamic lat/lon is needed, they could be passed via DAG params or fetched from another task/config
    result_path = weather.run(exec_date)
    ti.xcom_push(key="weather_path", value=result_path)
    return result_path

def _prepare_product_list_task(ti, **context):
    exec_date = _get_execution_date(context)
    product_list = []

    # Read from bronze inventory (produced by _ingest_inventory_task)
    inv_path = Path(part_dir("bronze", "inventory_dump", exec_date)) / "inventory.csv"
    if inv_path.exists():
        try:
            df_inv = pd.read_csv(inv_path)
            if "nama_produk" in df_inv.columns:
                product_list.extend(df_inv["nama_produk"].dropna().astype(str).tolist())
        except Exception as e:
            print(f"⚠️ Gagal membaca produk dari Inventory di task _prepare_product_list: {e}")

    # Read from local journal history file (source of truth from app.py)
    # The journal_history.csv is updated by app.py and is a direct input for sheets.py (which dumps to bronze)
    # For a robust Airflow DAG, if journal_history.csv is truly a dynamic source, it should be ingested
    # by its own task (which _ingest_sheets_task handles).
    # Here, we directly read the original 'journal_history.csv' as pipeline.py does for product list extraction.
    # Alternatively, this task could read the output of _ingest_sheets_task from the bronze layer.
    journal_path = Path("journal_history.csv") # Assuming this is accessible from Airflow worker
    if journal_path.exists():
        try:
            df_j = pd.read_csv(journal_path)
            for col in ["Day Products", "Night Products"]:
                if col in df_j.columns:
                    items = df_j[col].dropna().astype(str).str.split(",").sum()
                    if isinstance(items, list):
                        product_list.extend([x.strip() for x in items if x.strip()])
        except Exception as e:
            print(f"⚠️ Gagal membaca produk dari Journal di task _prepare_product_list: {e}")

    unique_products = list(set(filter(None, product_list))) # Remove duplicates and empty strings
    ti.xcom_push(key="product_list", value=unique_products)
    return unique_products


def _scrape_ingredients_task(ti, **context):
    exec_date = _get_execution_date(context)
    product_list = ti.xcom_pull(key="product_list", task_ids="prepare_product_list")
    
    if product_list is None:
        print("Product list is empty or not found. Skipping ingredient scraping.")
        ingredients_df = pd.DataFrame()
    else:
        ingredients_df = scrape_ingredients.run(exec_date, product_list=product_list)
        
    # ingredients_df will be used by build_silver (which reads from bronze layer HTML files)
    # and potentially by build_gold directly if needed (as in original pipeline.py)
    # For now, it mainly produces HTMLs in bronze layer and an index CSV.
    # The actual dataframe isn't pushed to XCom for later tasks directly,
    # as build_silver reads from the files.
    # However, for consistency with original pipeline, let's push it if build_gold expects it.
    
    # NOTE: XComs are not ideal for very large DataFrames.
    # If ingredients_df is huge, consider saving it to a temporary file in shared storage
    # and pushing the path to XCom instead.
    
    # Pushing the DataFrame itself to XCom
    # Airflow automatically serializes/deserializes Pandas DataFrames (if pandas is installed)
    ti.xcom_push(key="scraped_ingredients_df", value=ingredients_df)
    return ingredients_df.shape[0] # Return row count for logging


def _build_silver_task(ti, **context):
    exec_date = _get_execution_date(context)
    output_paths = build_silver.run(exec_date)
    ti.xcom_push(key="silver_output_paths", value=output_paths)
    return output_paths

def _build_gold_task(ti, **context):
    exec_date = _get_execution_date(context)
    # Pull the ingredients_df from _scrape_ingredients_task (if needed by gold directly)
    # As per original pipeline.py, ingredients_df was passed to build_gold
    ingredients_df_from_xcom = ti.xcom_pull(key="scraped_ingredients_df", task_ids="scrape_ingredients")
    
    # build_gold.run also accepts ingredients_df directly
    output_paths = build_gold.run(exec_date, ingredients_df=ingredients_df_from_xcom)
    ti.xcom_push(key="gold_output_paths", value=output_paths)
    return output_paths


with DAG(
    dag_id="skincare_granular_pipeline",
    schedule="@daily",
    start_date=days_ago(2), # Use days_ago for a relative start date
    catchup=False,
    tags=["skincare", "pipeline", "granular"],
    doc_md="""
    ## Skincare Granular ETL Pipeline
    
    This DAG breaks down the skincare ETL process into individual, manageable tasks.
    Each task corresponds to a specific ingestion or transformation step.
    """
) as dag:
    # --- Ingestion Tasks ---
    ingest_inventory_task = PythonOperator(
        task_id="ingest_inventory",
        python_callable=_ingest_inventory_task,
    )

    ingest_sheets_task = PythonOperator(
        task_id="ingest_sheets",
        python_callable=_ingest_sheets_task,
    )

    ingest_weather_task = PythonOperator(
        task_id="ingest_weather",
        python_callable=_ingest_weather_task,
    )

    # --- Product List Preparation Task ---
    # This task depends on inventory and sheets ingestion to gather product names
    prepare_product_list = PythonOperator(
        task_id="prepare_product_list",
        python_callable=_prepare_product_list_task,
    )

    # --- Scraping Task ---
    # This task depends on the product list being prepared
    scrape_ingredients_task = PythonOperator(
        task_id="scrape_ingredients",
        python_callable=_scrape_ingredients_task,
    )

    # --- Transformation Tasks ---
    # build_silver depends on all ingestions (its run function reads from bronze layer)
    # The current build_silver reads directly from paths based on date,
    # so direct XCom outputs from ingests are less critical, but dependency ordering is.
    build_silver_task = PythonOperator(
        task_id="build_silver",
        python_callable=_build_silver_task,
    )

    # build_gold depends on build_silver completion and potentially scraped ingredients dataframe
    build_gold_task = PythonOperator(
        task_id="build_gold",
        python_callable=_build_gold_task,
    )

    # Define task dependencies
    # Ingestions can run in parallel
    [ingest_inventory_task, ingest_sheets_task, ingest_weather_task] >> prepare_product_list
    
    # Scrape ingredients depends on the product list preparation
    prepare_product_list >> scrape_ingredients_task
    
    # Silver transformation depends on all ingestions and scraping (as it reads from bronze)
    # Ensure scrape_ingredients_task completes before build_silver_task starts,
    # as build_silver processes the HTMLs generated by scrape_ingredients.
    [ingest_inventory_task, ingest_sheets_task, ingest_weather_task, scrape_ingredients_task] >> build_silver_task
    
    # Gold transformation depends on silver transformation
    build_silver_task >> build_gold_task

