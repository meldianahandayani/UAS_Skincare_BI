from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import sys
import os
from sqlalchemy import create_engine, text

# --- 1. CONFIG PATH (SOLUSI ERROR MERAH "Module Not Found") ---
# Menambahkan folder root project ke sistem agar 'src' bisa dibaca oleh Python Airflow
sys.path.append('/opt/airflow')
sys.path.append('/opt/airflow/src')

# Import modul project
from src.pipeline import run_all
from src.utils.config import OWM_API_KEY
import requests

# --- 2. FUNGSI BANTUAN ---
def get_target_location():
    """
    Membaca kota terakhir yang dipilih user dari Database.
    Jika tidak ada data di DB, default ke Banjarmasin.
    """
    # Ambil URL DB dari Environment Variable
    db_url = os.getenv("DB_URL") 
    default_city = "Banjarmasin"
    
    if not db_url:
        print("⚠️ DB_URL tidak ditemukan di .env Airflow. Menggunakan default.")
        return default_city

    try:
        # --- SOLUSI KONEKSI DOCKER ---
        # Jika script jalan di dalam Docker Airflow, 'localhost' merujuk ke container itu sendiri.
        # Kita harus ubah jadi 'host.docker.internal' agar bisa akses database di host/container lain.
        if "localhost" in db_url:
            db_url = db_url.replace("localhost", "host.docker.internal")
            
        engine = create_engine(db_url)
        with engine.connect() as conn:
            # Pastikan tabel user_settings ada (defensive check)
            # Query ini mengambil setting kota terakhir
            result = conn.execute(text("SELECT setting_value FROM user_settings WHERE setting_key = 'current_city'"))
            row = result.fetchone()
            if row:
                return row[0]
    except Exception as e:
        print(f"⚠️ Gagal membaca preferensi user dari DB ({e}). Menggunakan default.")
    
    return default_city

def resolve_coords_manual(city):
    """Mencari lat/lon berdasarkan nama kota (Backup function jika modul geo bermasalah)"""
    if not OWM_API_KEY: return -3.3194, 114.5908 # Default BJM
    try:
        # Tambahkan ,ID untuk prioritas kota di Indonesia
        url = f"http://api.openweathermap.org/geo/1.0/direct?q={city},ID&limit=1&appid={OWM_API_KEY}"
        r = requests.get(url, timeout=10)
        if r.status_code == 200 and r.json():
            d = r.json()[0]
            return d["lat"], d["lon"]
    except: pass
    return -3.3194, 114.5908

def execute_pipeline_task(**kwargs):
    print("🚀 Memulai Pipeline Otomatis Skincare...")
    
    # 1. Cek User lagi dimana (Baca dari DB)
    target_city = get_target_location()
    print(f"📍 Target Lokasi User: {target_city}")
    
    # 2. Cari Koordinat Kota Tersebut
    lat, lon = resolve_coords_manual(target_city)
    print(f"🌍 Koordinat Target: {lat}, {lon}")
    
    # 3. Jalankan Pipeline Utama
    try:
        result = run_all(lat=lat, lon=lon)
        print(f"✅ SUKSES! Data tersimpan di: {result}")
    except Exception as e:
        print(f"❌ GAGAL MENJALANKAN PIPELINE: {e}")
        raise e 

# --- 3. DEFINISI DAG ---
default_args = {
    'owner': 'skincare_admin',
    'depends_on_past': False,
    'email_on_failure': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    'skincare_smart_scheduler', 
    default_args=default_args,
    description='Pipeline Otomatis Mengikuti Lokasi User',
    schedule_interval='0 6 * * *', # Jalan otomatis jam 06:00 Pagi setiap hari
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['skincare', 'production'],
) as dag:

    run_etl = PythonOperator(
        task_id='run_daily_etl_task',
        python_callable=execute_pipeline_task
    )