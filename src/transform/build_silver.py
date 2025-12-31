import json
import pandas as pd
import os
import s3fs
from datetime import date
from bs4 import BeautifulSoup

def _standardize_tracker_cols(df: pd.DataFrame) -> pd.DataFrame:
    """
    Standardize tracker columns from app.py schema to internal schema.
    
    Source of Truth (app.py): "Date", "Day Products", "Night Products", "Status"
    Target Schema (Internal): "tanggal_input", "produk_pagi", "produk_malam", "status_keamanan"
    """
    # Exact column mapping based on app.py schema
    exact_mapping = {
        "Date": "tanggal_input",
        "Day Products": "produk_pagi", 
        "Night Products": "produk_malam",
        "Status": "status_keamanan"
    }

    # Rename columns using exact mapping
    df = df.rename(columns=exact_mapping)

    # Ensure all expected columns exist
    expected_cols = ["tanggal_input", "produk_pagi", "produk_malam", "status_keamanan"]
    for col in expected_cols:
        if col not in df.columns:
            df[col] = None  # Add empty column if missing

    # Return only the expected columns in correct order
    return df[expected_cols]

def _parse_ingredients_from_html(html_path: str, fs) -> str:
    """Membaca file HTML CosDNA dari S3 dan mengekstrak ingredients."""
    try:
        with fs.open(html_path, 'r', encoding="utf-8", errors="replace") as f:
            content = f.read()
            
        soup = BeautifulSoup(content, "html.parser")
        
        ingredients = []
        rows = soup.find_all("tr", class_="iStuff")
        if not rows: rows = soup.find_all("tr")
        
        for tr in rows:
            tds = tr.find_all("td")
            if len(tds) >= 1:
                name = tds[0].get_text(strip=True)
                if name and "Ingredient" not in name and len(name) > 1:
                    ingredients.append(name)
                    
        return ", ".join(ingredients)
    except Exception as e:
        print(f"Warning: Error parsing {html_path}: {e}")
        return ""

def _safe_int(val) -> int:
    """Konversi aman ke integer, menangani string kosong, spasi, atau float string."""
    try:
        return int(float(str(val).strip()))
    except (ValueError, TypeError):
        return 0

def _clean_function_description(func_text: str) -> str:
    """
    Clean and standardize function descriptions for better display.
    Removes HTML tags and extra whitespace while preserving original technical terms.
    """
    if not func_text:
        return "Unknown"
    
    # Remove HTML tags and extra whitespace only
    import re
    func_clean = re.sub(r'<[^>]+>', '', func_text)
    func_clean = func_clean.strip()
    
    # Return cleaned version - preserve original technical terms
    return func_clean if len(func_clean) > 0 else "Unknown"

def _parse_detailed_json(html_path: str, fs) -> str:
    """Mengekstrak detail ingredients dari S3 ke JSON."""
    try:
        with fs.open(html_path, 'r', encoding="utf-8", errors="replace") as f:
            content = f.read()
            
        soup = BeautifulSoup(content, "html.parser")
        
        data = []
        rows = soup.find_all("tr", class_="iStuff")
        if not rows: rows = soup.find_all("tr")
        
        for tr in rows:
            tds = tr.find_all("td")
            if len(tds) >= 4:
                name = tds[0].get_text(strip=True)
                func = tds[1].get_text(strip=True)
                acne = tds[2].get_text(strip=True)
                irritant = tds[3].get_text(strip=True)
                
                if name and "Ingredient" not in name:
                    data.append({
                        "Ingredient": name, 
                        "Function": _clean_function_description(func), 
                        "Acne": _safe_int(acne), 
                        "Irritant": _safe_int(irritant),
                        "Safety": tds[4].get_text(strip=True) if len(tds) > 4 else None
                    })
        
        return json.dumps(data)
    except Exception as e:
        print(f"❌ Error parsing detailed JSON for {html_path}: {e}")
        return "[]"

def run(d: date) -> dict:
    # MinIO Setup
    is_docker = os.path.exists("/.dockerenv")
    default_host = "minio" if is_docker else "localhost"
    minio_endpoint = os.getenv("MINIO_ENDPOINT", f"http://{default_host}:9000")
    
    storage_options = {
        "key": os.getenv("MINIO_ACCESS_KEY", "skincare_admin"),
        "secret": os.getenv("MINIO_SECRET_KEY", "skincare_password"),
        "client_kwargs": {"endpoint_url": minio_endpoint}
    }
    
    fs = s3fs.S3FileSystem(**storage_options)
    bucket = "datalake"

    # Path Input (Bronze - S3)
    inv_path = f"s3://{bucket}/bronze/inventory/date={d}/inventory.csv"
    trk_path = f"s3://{bucket}/bronze/sheets/date={d}/tracker.csv"
    wth_path = f"s3://{bucket}/bronze/weather/date={d}/weather.json"
    ing_index_path = f"s3://{bucket}/bronze/ingredients_html/date={d}/scraped_index.csv"

    # --- 1. PROSES TRACKER (SHEETS) ---
    if fs.exists(trk_path):
        trk = pd.read_csv(trk_path, storage_options=storage_options)
        # Panggil fungsi standarisasi baru di atas
        trk = _standardize_tracker_cols(trk)
        
        # Pastikan format tanggal benar
        trk["tanggal_input"] = pd.to_datetime(trk["tanggal_input"], errors="coerce").dt.date.astype(str)
        
        # Simpan ke Silver (Parquet)
        trk_out = f"s3://{bucket}/silver/tracker/date={d}/tracker.parquet"
        trk.to_parquet(trk_out, index=False, storage_options=storage_options)
        print(f"✅ Silver Tracker saved: {trk_out}")
    else:
        trk_out = None

    # --- 2. PROSES INVENTORY (SQL) ---
    if fs.exists(inv_path):
        inv = pd.read_csv(inv_path, storage_options=storage_options)
        # Standarisasi tanggal inventory
        for col in ["tanggal_buka", "tanggal_kadaluwarsa"]:
            if col in inv.columns:
                inv[col] = pd.to_datetime(inv[col], errors="coerce").dt.date
        
        inv_out = f"s3://{bucket}/silver/inventory/date={d}/inventory.parquet"
        inv.to_parquet(inv_out, index=False, storage_options=storage_options)
        print(f"✅ Silver Inventory saved: {inv_out}")
    else:
        inv_out = None

    # --- 3. PROSES WEATHER ---
    if fs.exists(wth_path):
        with fs.open(wth_path, 'r', encoding='utf-8') as f:
            raw = json.load(f)
            
        current = raw.get("current", {})
        env = pd.DataFrame([{
            "tanggal": str(d),
            "uvi": current.get("uvi"),
            "humidity": current.get("humidity"),
            "temp_c": current.get("temp"),
        }])
        env_out = f"s3://{bucket}/silver/weather/date={d}/weather.parquet"
        env.to_parquet(env_out, index=False, storage_options=storage_options)
        print(f"✅ Silver Weather saved: {env_out}")
    else:
        env_out = None
        
    # --- 4. PROSES INGREDIENTS ---
    if fs.exists(ing_index_path):
        # Baca index mapping (Nama Produk -> Path HTML)
        ing_df = pd.read_csv(ing_index_path, storage_options=storage_options)
        # Lakukan parsing HTML untuk mendapatkan ingredients list
        ing_df["ingredients_list"] = ing_df["html_path"].apply(lambda x: _parse_ingredients_from_html(x, fs))
        ing_df["detailed_analysis"] = ing_df["html_path"].apply(lambda x: _parse_detailed_json(x, fs))
        
        # Debugging Log: Tampilkan jumlah produk yang memiliki data detail
        count_with_data = ing_df[ing_df["detailed_analysis"] != "[]"].shape[0]
        print(f"📊 Silver Layer: Berhasil mengekstrak detail ingredients untuk {count_with_data} dari {len(ing_df)} produk.")
        
        # Cek sampel data berbahaya untuk verifikasi
        sample_risk = ing_df[ing_df["detailed_analysis"].str.contains('"acne": [3-5]', regex=True)]
        if not sample_risk.empty:
            print(f"⚠️  Terdeteksi {len(sample_risk)} produk dengan Acne Score >= 3 di Silver Layer.")
        
        ing_out = f"s3://{bucket}/silver/ingredients/date={d}/ingredients.parquet"
        ing_df[["nama_produk", "ingredients_list", "detailed_analysis"]].to_parquet(ing_out, index=False, storage_options=storage_options)
        print(f"✅ Silver Ingredients saved: {ing_out}")
    else:
        ing_out = None

    return {
        "inventory": inv_out,
        "tracker": trk_out,
        "weather": env_out,
        "ingredients": ing_out,
    }