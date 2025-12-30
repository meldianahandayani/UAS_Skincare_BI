from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.models import Variable
from datetime import datetime, timedelta
import pendulum
import sys

# Menambahkan path /opt/airflow ke system path agar bisa import module src
# Ini diperlukan karena struktur folder di dalam container Airflow
sys.path.append("/opt/airflow")

# Setting Timezone ke WIB (Asia/Jakarta)
local_tz = pendulum.timezone("Asia/Jakarta")

# Koordinat Default (Banjarmasin)
# Menggunakan koordinat yang sama dengan default di app.py
DEFAULT_LAT = -3.3194
DEFAULT_LON = 114.5908

default_args = {
    'owner': 'skincare_admin',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    'daily_skincare_pipeline_sync',
    default_args=default_args,
    description='Menjalankan sinkronisasi data pipeline skincare setiap hari jam 06:00 WIB',
    schedule_interval='0 6 * * *',  # Cron expression: Menit 0, Jam 6, Setiap Hari
    start_date=datetime(2024, 1, 1, tzinfo=local_tz),
    catchup=False,
    tags=['skincare', 'etl', 'daily'],
) as dag:

    def execute_pipeline_task(**kwargs):
        """
        Task wrapper untuk menjalankan logika pipeline.
        """
        # Import di dalam fungsi untuk memastikan module src terbaca saat runtime worker
        from src.pipeline import run_all

        # Ambil koordinat dari Airflow Variable agar bisa diubah via UI tanpa edit code
        # Default tetap ke Banjarmasin jika variable belum diset di Admin -> Variables
        target_lat = float(Variable.get("skincare_target_lat", default_var=DEFAULT_LAT))
        target_lon = float(Variable.get("skincare_target_lon", default_var=DEFAULT_LON))

        execution_date = kwargs.get('ds')
        print(f"[{execution_date}] Memulai Daily Pipeline Sync...")
        print(f"Lokasi Target: Lat {target_lat}, Lon {target_lon}")
        
        # Menjalankan pipeline (Ingest -> Process -> Gold)
        run_all(lat=target_lat, lon=target_lon)
        print("Pipeline berhasil dijalankan.")

    run_sync = PythonOperator(
        task_id='run_daily_sync_process',
        python_callable=execute_pipeline_task,
    )