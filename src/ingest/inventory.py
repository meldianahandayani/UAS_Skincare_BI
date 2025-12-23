import pandas as pd
from datetime import date
from sqlalchemy import create_engine

from src.utils.config import DB_URL
from src.utils.paths import part_dir, ensure_dir

def run(d: date) -> str:
    if not DB_URL:
        raise RuntimeError("DB_URL belum diisi di .env")

    engine = create_engine(DB_URL)
    df = pd.read_sql("SELECT * FROM inventory_skincare;", engine)

    out_dir = ensure_dir(part_dir("bronze", "inventory_dump", d))
    out_path = out_dir / "inventory.csv"
    df.to_csv(out_path, index=False)
    return str(out_path)