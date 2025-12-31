import pandas as pd
import os
from datetime import date
from sqlalchemy import create_engine

from src.utils.config import DB_URL

def run(d: date) -> str:
    if not DB_URL:
        raise RuntimeError("DB_URL belum diisi di .env")

    engine = create_engine(DB_URL)
    df = pd.read_sql("SELECT * FROM inventory_skincare;", engine)

    # MinIO Config
    is_docker = os.path.exists("/.dockerenv")
    default_host = "minio" if is_docker else "localhost"
    minio_endpoint = os.getenv("MINIO_ENDPOINT", f"http://{default_host}:9000")
    storage_options = {
        "key": os.getenv("MINIO_ACCESS_KEY", "skincare_admin"),
        "secret": os.getenv("MINIO_SECRET_KEY", "skincare_password"),
        "client_kwargs": {"endpoint_url": minio_endpoint}
    }

    s3_path = f"s3://datalake/bronze/inventory/date={d}/inventory.csv"
    df.to_csv(s3_path, index=False, storage_options=storage_options)
    
    print(f"💾 Saved inventory to MinIO: {s3_path}")
    return s3_path