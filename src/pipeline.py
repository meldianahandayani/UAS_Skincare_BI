from datetime import date

from src.ingest.inventory import run as ingest_inventory
from src.ingest.sheets import run as ingest_sheets
from src.ingest.weather import run as ingest_weather
from src.ingest.scrape_ingredients import run as ingest_scrape

from src.transform.build_silver import run as build_silver
from src.transform.build_gold import run as build_gold

# Tambahkan argumen lat=None, lon=None
def run_all(lat=None, lon=None):
    d = date.today()

    print("🚀 Memulai Pipeline...")

    # Jalankan Ingestion
    inv_path = ingest_inventory(d)
    sheets_path = ingest_sheets(d)
    
    # Kirim lat/lon ke ingest_weather
    weather_path = ingest_weather(d, lat=lat, lon=lon)

    ingredients_df = ingest_scrape(d, pages_csv_path="sources/product_pages.csv")

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
            "scrape_rows": int(len(ingredients_df)),
        },
        "silver": silver_paths,
        "gold": gold_paths,
    }