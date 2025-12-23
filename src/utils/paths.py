from pathlib import Path
from datetime import date

BASE = Path("datalake")

def part_dir(layer: str, name: str, d: date) -> Path:
    return BASE / layer / name / f"date={d.isoformat()}"

def ensure_dir(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p
