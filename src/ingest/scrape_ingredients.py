import re
import time
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import date

from src.utils.paths import part_dir, ensure_dir

def _safe_name(s: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "_", s).strip("_")[:120]

def extract_ingredients_list(html: str) -> list[str]:
    soup = BeautifulSoup(html, "lxml")

    # Strategi 1: INCIDecoder biasanya punya list ingredient dengan link <a>
    cand = []
    for sel in ["div.ingredlist a", "#ingredlist a", "div#ingredlist a"]:
        nodes = soup.select(sel)
        if nodes:
            cand = [n.get_text(" ", strip=True) for n in nodes if n.get_text(strip=True)]
            break
    if cand:
        return cand

    # Strategi 2: cari teks setelah kata "Ingredients"
    text = soup.get_text(" ", strip=True)
    m = re.search(r"(Ingredients|INGREDIENTS)\s*[:\-]?\s*(.+)", text)
    if m:
        tail = m.group(2)
        # ambil secukupnya biar nggak kepanjangan
        tail = tail[:2000]
        parts = re.split(r",|;|\|", tail)
        return [p.strip() for p in parts if p.strip()]

    return []

def conflict_rules_from_ingredients(ings: list[str]) -> list[str]:
    low = " ".join(i.lower() for i in ings)
    rules = []

    if "retinol" in low or "retino" in low:
        rules.append("Retinoid: hindari bareng AHA/BHA pada malam yang sama jika kulit sensitif.")
    if any(k in low for k in ["glycolic", "lactic", "salicylic", "aha", "bha", "pha"]):
        rules.append("Exfoliant: jika kulit kemerahan/iritasi, jadikan recovery night (hindari eksfoliasi).")
    if "ascorbic" in low or "vitamin c" in low:
        rules.append("Vitamin C: gunakan sunscreen pada siang hari.")
    return rules

def run(d: date, pages_csv_path: str = "sources/product_pages.csv") -> pd.DataFrame:
    pages = pd.read_csv(pages_csv_path)

    out_html_dir = ensure_dir(part_dir("bronze", "ingredients_html", d))
    out_parsed_dir = ensure_dir(part_dir("bronze", "ingredients_parsed", d))

    rows = []
    for _, r in pages.iterrows():
        brand = str(r.get("nama_brand", "")).strip()
        product = str(r.get("nama_produk", "")).strip()
        url = str(r.get("url", "")).strip()

        html_path = ""
        ings = []
        rules = []

        if url and url.lower() != "nan":
            resp = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
            resp.raise_for_status()

            fname = _safe_name(f"{brand}__{product}") + ".html"
            html_file = out_html_dir / fname
            html_file.write_text(resp.text, encoding="utf-8")
            html_path = str(html_file)

            ings = extract_ingredients_list(resp.text)
            rules = conflict_rules_from_ingredients(ings)

            time.sleep(1)  # biar tidak spam request

        rows.append({
            "nama_brand": brand,
            "nama_produk": product,
            "url": url,
            "ingredients_list": "|".join(ings),
            "conflict_rules": " | ".join(rules),
            "html_path": html_path
        })

    df = pd.DataFrame(rows)

    # simpan hasil parsing ke bronze juga, supaya silver bisa baca dari file
    parsed_path = out_parsed_dir / "ingredients.csv"
    df.to_csv(parsed_path, index=False)

    return df