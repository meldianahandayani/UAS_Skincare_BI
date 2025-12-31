import pandas as pd
import os
from datetime import date
from pathlib import Path

def run(d: date) -> str:
    """
    Ingest journal data from local CSV file.
    Reads from journal_history.csv which contains the actual data from app.py
    """
    # Read from local journal history file (source of truth from app.py)
    journal_csv_path = Path("journal_history.csv")
    
    if not journal_csv_path.exists():
        # Create empty DataFrame with expected columns if file doesn't exist
        df = pd.DataFrame(columns=["Date", "Day Products", "Night Products", "Status"])
        print("⚠️ journal_history.csv not found. Creating empty tracker data.")
    else:
        df = pd.read_csv(journal_csv_path)
        print(f"📊 Loaded {len(df)} journal entries from journal_history.csv")

    # MinIO Config
    is_docker = os.path.exists("/.dockerenv")
    default_host = "minio" if is_docker else "localhost"
    minio_endpoint = os.getenv("MINIO_ENDPOINT", f"http://{default_host}:9000")
    storage_options = {
        "key": os.getenv("MINIO_ACCESS_KEY", "skincare_admin"),
        "secret": os.getenv("MINIO_SECRET_KEY", "skincare_password"),
        "client_kwargs": {"endpoint_url": minio_endpoint}
    }

    s3_path = f"s3://datalake/bronze/sheets/date={d}/tracker.csv"
    df.to_csv(s3_path, index=False, storage_options=storage_options)
    
    print(f"💾 Saved tracker data to MinIO: {s3_path}")
    return s3_path
