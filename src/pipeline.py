from datetime import date
import pandas as pd
from pathlib import Path

from src.ingest.inventory import run as ingest_inventory
from src.ingest.sheets import run as ingest_sheets
from src.ingest.weather import run as ingest_weather
from src.ingest.scrape_ingredients import run as ingest_scrape

from src.transform.build_silver import run as build_silver
from src.transform.build_gold import run as build_gold

def run_all(lat=None, lon=None):
    d = date.today()

    print("🚀 Memulai Pipeline...")

    # Jalankan Ingestion
    inv_path = ingest_inventory(d)
    sheets_path = ingest_sheets(d)
    
    # Kirim lat/lon ke ingest_weather
    weather_path = ingest_weather(d, lat=lat, lon=lon)

    # Jalankan Scraping (Ingest Raw HTML ke Bronze)
    product_list = []
    
    # 1. Ambil produk dari Inventory (agar semua stok discrap)
    if inv_path and Path(inv_path).exists():
        try:
            df_inv = pd.read_csv(inv_path)
            if "nama_produk" in df_inv.columns:
                product_list.extend(df_inv["nama_produk"].dropna().astype(str).tolist())
        except Exception as e:
            print(f"⚠️ Gagal membaca produk dari Inventory: {e}")

    # 2. Ambil produk dari Journal
    journal_path = Path("journal_history.csv")
    
    if journal_path.exists():
        try:
            df_j = pd.read_csv(journal_path)
            # Ambil semua produk dari kolom Day dan Night, pisahkan koma
            for col in ["Day Products", "Night Products"]:
                if col in df_j.columns:
                    items = df_j[col].dropna().astype(str).str.split(",").sum()
                    if isinstance(items, list):
                        product_list.extend([x.strip() for x in items if x.strip()])
        except Exception as e:
            print(f"⚠️ Gagal membaca produk dari Journal: {e}")

    ingredients_df = ingest_scrape(d, product_list=product_list)

    # Jalankan Transformasi (Silver & Gold)
    silver_paths = build_silver(d)
    gold_paths = build_gold(d, ingredients_df)

    print("🏁 Pipeline Selesai.")

    return {
        "date": str(d),
        "location": f"{lat},{lon}" if lat else "Default .env",
        "bronze": {
            "inventory": inv_path,
            "sheets": sheets_path,
            "weather": weather_path,
            "scrape_rows": 0,
        },
        "silver": silver_paths,
        "gold": gold_paths,
    }