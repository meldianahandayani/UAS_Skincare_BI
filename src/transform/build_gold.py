import pandas as pd
import duckdb
from datetime import date, datetime
from pathlib import Path
from sqlalchemy import create_engine

from src.utils.config import DB_URL
from src.utils.paths import part_dir, ensure_dir
from src.recommend.rules import make_recommendation

def run(d: date, ingredients_df: pd.DataFrame) -> dict:
    # baca silver
    inv_path = Path(part_dir("silver", "inventory", d)) / "inventory.parquet"
    trk_path = Path(part_dir("silver", "tracker", d)) / "tracker.parquet"
    wth_path = Path(part_dir("silver", "weather", d)) / "weather.parquet"
    ing_path = Path(part_dir("silver", "ingredients", d)) / "ingredients.parquet"

    con = duckdb.connect(database=":memory:")

    con.execute(f"CREATE VIEW inv AS SELECT * FROM read_parquet('{inv_path.as_posix()}')")
    con.execute(f"CREATE VIEW trk AS SELECT * FROM read_parquet('{trk_path.as_posix()}')")
    con.execute(f"CREATE VIEW wth AS SELECT * FROM read_parquet('{wth_path.as_posix()}')")
    con.execute(f"CREATE VIEW ing AS SELECT * FROM read_parquet('{ing_path.as_posix()}')")


    # ambil tracker hari ini; kalau tidak ada, ambil baris terakhir
    daily = con.execute("""
        WITH t AS (
          SELECT * FROM trk WHERE tanggal_input = ?
        ),
        last_t AS (
          SELECT * FROM trk ORDER BY tanggal_input DESC LIMIT 1
        )
        SELECT
          wth.tanggal,
          wth.uvi, wth.humidity, wth.temp_c, wth.weather_main,
          COALESCE(t.kondisi_kulit, last_t.kondisi_kulit) AS kondisi_kulit,
          COALESCE(t.penggunaan_bahan_aktif, last_t.penggunaan_bahan_aktif) AS penggunaan_bahan_aktif,
          COALESCE(t.reaksi_kulit, last_t.reaksi_kulit) AS reaksi_kulit
        FROM wth
        LEFT JOIN t ON TRUE
        LEFT JOIN last_t ON TRUE
    """, [str(d)]).df()

    # inventory check: apakah ada sunscreen?
    inv_df = con.execute("SELECT kategori, tanggal_kedaluwarsa FROM inv").df()
    has_sunscreen = False
    if "kategori" in inv_df.columns:
        has_sunscreen = (inv_df["kategori"].astype(str).str.lower() == "sunscreen").any()

    # conflict notes dari scraping (gabungkan ringkas)
    notes = ""
    if isinstance(ingredients_df, pd.DataFrame) and "conflict_rules" in ingredients_df.columns:
        lst = [x for x in ingredients_df["conflict_rules"].fillna("").tolist() if x.strip()]
        notes = " | ".join(lst[:6])  # batasi biar nggak kepanjangan

    row = daily.iloc[0].to_dict()
    am, pm, warn = make_recommendation(
        row.get("uvi"),
        row.get("humidity"),
        row.get("kondisi_kulit"),
        row.get("reaksi_kulit"),
        has_sunscreen=has_sunscreen,
        conflict_notes=notes
    )

    rec = pd.DataFrame([{
        "tanggal": row.get("tanggal"),
        "am_plan": am,
        "pm_plan": pm,
        "warnings": warn
    }])

    # simpan gold
    gold_daily_dir = ensure_dir(part_dir("gold", "daily_context", d))
    gold_rec_dir = ensure_dir(part_dir("gold", "recommendation", d))

    daily_out = gold_daily_dir / "daily_context.parquet"
    rec_out = gold_rec_dir / "recommendation.parquet"

    daily.to_parquet(daily_out, index=False)
    rec.to_parquet(rec_out, index=False)

    # (opsional) load ke postgres daily_analysis (append)
    if DB_URL:
        try:
            engine = create_engine(DB_URL)
            to_dw = pd.DataFrame([{
                "tanggal": datetime.now().date(),
                "uvi": row.get("uvi"),
                "humidity": row.get("humidity"),
                "temp_c": row.get("temp_c"),
                "weather_main": row.get("weather_main"),
                "rekomendasi": f"{am} || {pm} || {warn}"
            }])
            to_dw.to_sql("daily_analysis", engine, if_exists="append", index=False)
        except:
            pass

    return {
        "gold_daily_context": str(daily_out),
        "gold_recommendation": str(rec_out),
    }