import pandas as pd
from datetime import date

from src.utils.config import SHEET_CSV_URL
from src.utils.paths import part_dir, ensure_dir

def run(d: date) -> str:
    if not SHEET_CSV_URL:
        raise RuntimeError("SHEET_CSV_URL belum diisi di .env")

    df = pd.read_csv(SHEET_CSV_URL)

    out_dir = ensure_dir(part_dir("bronze", "skin_tracker", d))
    out_path = out_dir / "tracker.csv"
    df.to_csv(out_path, index=False)
    return str(out_path)