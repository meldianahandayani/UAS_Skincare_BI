import pandas as pd
from datetime import date
from pathlib import Path

from src.utils.paths import part_dir, ensure_dir

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

    # Ensure output directory exists and save to bronze layer
    out_dir = ensure_dir(part_dir("bronze", "skin_tracker", d))
    out_path = out_dir / "tracker.csv"
    df.to_csv(out_path, index=False)
    
    print(f"💾 Saved tracker data to: {out_path}")
    return str(out_path)
