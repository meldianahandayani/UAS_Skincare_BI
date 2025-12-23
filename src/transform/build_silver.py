import json
import pandas as pd
from datetime import date
from pathlib import Path

from src.utils.paths import part_dir, ensure_dir

def _standardize_tracker_cols(df: pd.DataFrame) -> pd.DataFrame:
    # coba map beberapa variasi nama kolom umum
    mapping_candidates = {
        "tanggal_input": ["tanggal_input", "tanggal", "date"],
        "kondisi_kulit": ["kondisi_kulit", "kondisi", "skin_condition"],
        "penggunaan_bahan_aktif": ["penggunaan_bahan_aktif", "pakai_active", "active", "active_used"],
        "reaksi_kulit": ["reaksi_kulit", "reaksi", "reaction"]
    }

    rename_map = {}
    cols_lower = {c.lower(): c for c in df.columns}

    for target, opts in mapping_candidates.items():
        for opt in opts:
            if opt in cols_lower:
                rename_map[cols_lower[opt]] = target
                break

    df = df.rename(columns=rename_map)

    # pastikan kolom target ada
    for col in ["tanggal_input", "kondisi_kulit", "penggunaan_bahan_aktif", "reaksi_kulit"]:
        if col not in df.columns:
            df[col] = None

    return df[["tanggal_input", "kondisi_kulit", "penggunaan_bahan_aktif", "reaksi_kulit"]]

def run(d: date) -> dict:
    inv_path = Path(part_dir("bronze", "inventory_dump", d)) / "inventory.csv"
    trk_path = Path(part_dir("bronze", "skin_tracker", d)) / "tracker.csv"
    wth_path = Path(part_dir("bronze", "weather_raw", d)) / "weather.json"
    ing_path = Path(part_dir("bronze", "ingredients_parsed", d)) / "ingredients.csv"

    if not inv_path.exists():
        raise FileNotFoundError(f"Bronze inventory belum ada: {inv_path}")
    if not trk_path.exists():
        raise FileNotFoundError(f"Bronze tracker belum ada: {trk_path}")
    if not wth_path.exists():
        raise FileNotFoundError(f"Bronze weather belum ada: {wth_path}")
    if not ing_path.exists():
        raise FileNotFoundError(f"Bronze ingredients parsed belum ada: {ing_path}")

    # Inventory
    inv = pd.read_csv(inv_path)
    for col in ["tanggal_beli", "tanggal_buka", "tanggal_kedaluwarsa"]:
        if col in inv.columns:
            inv[col] = pd.to_datetime(inv[col], errors="coerce").dt.date

    inv_dir = ensure_dir(part_dir("silver", "inventory", d))
    inv_out = inv_dir / "inventory.parquet"
    inv.to_parquet(inv_out, index=False)

    # Tracker
    trk = pd.read_csv(trk_path)
    trk = _standardize_tracker_cols(trk)
    trk["tanggal_input"] = pd.to_datetime(trk["tanggal_input"], errors="coerce").dt.date.astype(str)

    trk_dir = ensure_dir(part_dir("silver", "tracker", d))
    trk_out = trk_dir / "tracker.parquet"
    trk.to_parquet(trk_out, index=False)

    # Weather (flatten)
    raw = json.loads(wth_path.read_text(encoding="utf-8"))
    current = raw.get("current", {})
    weather_main = None
    if isinstance(current.get("weather"), list) and current["weather"]:
        weather_main = current["weather"][0].get("main")

    env = pd.DataFrame([{
        "tanggal": str(d),
        "uvi": current.get("uvi"),
        "humidity": current.get("humidity"),
        "temp_c": current.get("temp"),
        "weather_main": weather_main
    }])

    env_dir = ensure_dir(part_dir("silver", "weather", d))
    env_out = env_dir / "weather.parquet"
    env.to_parquet(env_out, index=False)

    # Ingredients parsed
    ing = pd.read_csv(ing_path)
    ing_dir = ensure_dir(part_dir("silver", "ingredients", d))
    ing_out = ing_dir / "ingredients.parquet"
    ing.to_parquet(ing_out, index=False)

    return {
        "inventory": str(inv_out),
        "tracker": str(trk_out),
        "weather": str(env_out),
        "ingredients": str(ing_out),
    }