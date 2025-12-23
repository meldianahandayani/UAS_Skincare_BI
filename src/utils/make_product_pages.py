import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv
import os
from pathlib import Path

load_dotenv()

DB_URL = os.getenv("DB_URL")  # contoh: postgresql://admin:admin@localhost:5432/skincare_db

def main():
    engine = create_engine(DB_URL)
    df = pd.read_sql("""
        SELECT DISTINCT nama_brand, nama_produk
        FROM inventory_skincare
        ORDER BY nama_brand, nama_produk
    """, engine)

    # bikin kolom url kosong dulu (nanti kamu isi)
    df["url"] = ""

    Path("sources").mkdir(parents=True, exist_ok=True)
    out_path = Path("sources/product_pages.csv")
    df.to_csv(out_path, index=False)
    print(f"✅ Dibuat: {out_path} (isi URL masih kosong)")

if __name__ == "__main__":
    main()