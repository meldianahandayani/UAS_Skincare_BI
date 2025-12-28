import json
import pandas as pd
from datetime import date
from pathlib import Path
from bs4 import BeautifulSoup
from src.utils.paths import part_dir, ensure_dir

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

def _parse_ingredients_from_html(html_path: str) -> str:
    """Membaca file HTML CosDNA dan mengekstrak ingredients menggunakan parser baru."""
    try:
        p = Path(html_path)
        if not p.exists(): return ""
        
        content = p.read_text(encoding="utf-8", errors="replace")
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

def _parse_detailed_json(html_path: str) -> str:
    """Mengekstrak detail ingredients (Function, Acne/Irritant score) ke JSON menggunakan parser baru."""
    try:
        p = Path(html_path)
        if not p.exists(): return "[]"
        
        content = p.read_text(encoding="utf-8", errors="replace")
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
    # Path Input (Bronze)
    inv_path = Path(part_dir("bronze", "inventory_dump", d)) / "inventory.csv"
    trk_path = Path(part_dir("bronze", "skin_tracker", d)) / "tracker.csv"
    wth_path = Path(part_dir("bronze", "weather_raw", d)) / "weather.json"
    ing_index_path = Path(part_dir("bronze", "ingredients_html", d)) / "scraped_index.csv"

    # --- 1. PROSES TRACKER (SHEETS) ---
    if trk_path.exists():
        trk = pd.read_csv(trk_path)
        # Panggil fungsi standarisasi baru di atas
        trk = _standardize_tracker_cols(trk)
        
        # Pastikan format tanggal benar
        trk["tanggal_input"] = pd.to_datetime(trk["tanggal_input"], errors="coerce").dt.date.astype(str)
        
        # Simpan ke Silver (Parquet)
        trk_dir = ensure_dir(part_dir("silver", "tracker", d))
        trk_out = trk_dir / "tracker.parquet"
        trk.to_parquet(trk_out, index=False)
    else:
        trk_out = "Not Found"

    # --- 2. PROSES INVENTORY (SQL) ---
    if inv_path.exists():
        inv = pd.read_csv(inv_path)
        # Standarisasi tanggal inventory
        for col in ["tanggal_buka", "tanggal_kadaluwarsa"]:
            if col in inv.columns:
                inv[col] = pd.to_datetime(inv[col], errors="coerce").dt.date
        
        inv_dir = ensure_dir(part_dir("silver", "inventory", d))
        inv_out = inv_dir / "inventory.parquet"
        inv.to_parquet(inv_out, index=False)
    else:
        inv_out = "Not Found"

    # --- 3. PROSES WEATHER ---
    if wth_path.exists():
        raw = json.loads(wth_path.read_text(encoding="utf-8"))
        # (Logika weather tetap sama seperti sebelumnya, disingkat disini agar fokus)
        current = raw.get("current", {})
        env = pd.DataFrame([{
            "tanggal": str(d),
            "uvi": current.get("uvi"),
            "humidity": current.get("humidity"),
            "temp_c": current.get("temp"),
        }])
        env_dir = ensure_dir(part_dir("silver", "weather", d))
        env_out = env_dir / "weather.parquet"
        env.to_parquet(env_out, index=False)
    else:
        env_out = "Not Found"
        
    # --- 4. PROSES INGREDIENTS ---
    if ing_index_path.exists():
        # Baca index mapping (Nama Produk -> Path HTML)
        ing_df = pd.read_csv(ing_index_path)
        # Lakukan parsing HTML untuk mendapatkan ingredients list
        ing_df["ingredients_list"] = ing_df["html_path"].apply(_parse_ingredients_from_html)
        ing_df["detailed_analysis"] = ing_df["html_path"].apply(_parse_detailed_json)
        
        # Debugging Log: Tampilkan jumlah produk yang memiliki data detail
        count_with_data = ing_df[ing_df["detailed_analysis"] != "[]"].shape[0]
        print(f"📊 Silver Layer: Berhasil mengekstrak detail ingredients untuk {count_with_data} dari {len(ing_df)} produk.")
        
        # Cek sampel data berbahaya untuk verifikasi
        sample_risk = ing_df[ing_df["detailed_analysis"].str.contains('"acne": [3-5]', regex=True)]
        if not sample_risk.empty:
            print(f"⚠️  Terdeteksi {len(sample_risk)} produk dengan Acne Score >= 3 di Silver Layer.")
        
        ing_dir = ensure_dir(part_dir("silver", "ingredients", d))
        ing_out = ing_dir / "ingredients.parquet"
        ing_df[["nama_produk", "ingredients_list", "detailed_analysis"]].to_parquet(ing_out, index=False)
    else:
        ing_out = "Not Found"

    return {
        "inventory": str(inv_out),
        "tracker": str(trk_out),
        "weather": str(env_out),
        "ingredients": str(ing_out),
    }