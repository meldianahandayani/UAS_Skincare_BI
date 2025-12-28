import re
import time
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import date
from urllib.parse import quote_plus

from src.utils.paths import part_dir, ensure_dir

def _safe_name(s: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "_", s).strip("_")[:120]

def search_cosdna_url(product_name: str) -> str:
    """Mencari URL produk di CosDNA berdasarkan nama."""
    try:
        safe_query = quote_plus(product_name)
        search_url = f"https://cosdna.com/eng/product.php?q={safe_query}"
        headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://cosdna.com/"}
        resp = requests.get(search_url, headers=headers, timeout=10)
        
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.content, "html.parser")
            all_links = soup.find_all("a", href=True)
            for link in all_links:
                href = link['href']
                # Ambil link produk kosmetik yang valid
                if "cosmetic_" in href:
                    return href if "http" in href else f"https://cosdna.com/eng/{href}"
    except Exception as e:
        print(f"⚠️ Search failed for {product_name}: {e}")
    return ""

def run(d: date, product_list: list[str] = None) -> pd.DataFrame:
    out_html_dir = ensure_dir(part_dir("bronze", "ingredients_html", d))

    if not product_list:
        return pd.DataFrame()

    # Hapus duplikat nama produk
    unique_products = list(set(product_list))
    print(f"🕷️ Processing {len(unique_products)} unique products from Journal & Inventory...")

    rows = []
    for prod in unique_products:
        prod = prod.strip()
        if not prod: continue

        # 1. Cari URL otomatis
        url = search_cosdna_url(prod)
        html_path = ""

        if url:
            try:
                # Fix double slashes in URL - remove /eng//eng/
                fixed_url = url.replace("/eng//eng/", "/eng/")
                print(f"🔗 Fixed URL for {prod}: {fixed_url}")
                
                # 2. Download HTML
                resp = requests.get(fixed_url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
                if resp.status_code == 200:
                    # Verify we got actual content (not an error page)
                    if len(resp.text) > 1000 and "cosmetic" in resp.text.lower():
                        fname = _safe_name(prod) + ".html"
                        html_file = out_html_dir / fname
                        html_file.write_text(resp.text, encoding="utf-8")
                        html_path = str(html_file)
                        print(f"✅ Scraped: {prod} ({len(resp.text)} chars)")
                    else:
                        print(f"⚠️ Warning: Content too short or invalid for {prod}")
                else:
                    print(f"❌ HTTP {resp.status_code} for {prod}: {fixed_url}")
            except Exception as e:
                print(f"❌ Error scraping {prod}: {e}")
        else:
            print(f"⚠️ URL not found for: {prod}")

        rows.append({
            "nama_produk": prod,
            "url": url,
            "html_path": html_path,
            "scraped_date": d
        })

    df = pd.DataFrame(rows)
    
    # Simpan index metadata agar Silver layer tahu mapping file HTML ke Nama Produk
    if not df.empty:
        df.to_csv(out_html_dir / "scraped_index.csv", index=False)

    return df