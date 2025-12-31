import re
import time
import os
import s3fs
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import date
from urllib.parse import quote_plus

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
    # MinIO Setup
    is_docker = os.path.exists("/.dockerenv")
    default_host = "minio" if is_docker else "localhost"
    minio_endpoint = os.getenv("MINIO_ENDPOINT", f"http://{default_host}:9000")
    fs = s3fs.S3FileSystem(
        key=os.getenv("MINIO_ACCESS_KEY", "skincare_admin"),
        secret=os.getenv("MINIO_SECRET_KEY", "skincare_password"),
        client_kwargs={'endpoint_url': minio_endpoint}
    )
    
    base_s3_path = f"datalake/bronze/ingredients_html/date={d}"

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
                        target_path = f"{base_s3_path}/{fname}"
                        with fs.open(target_path, "wb") as f:
                            f.write(resp.content)
                        html_path = f"s3://{target_path}"
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
        with fs.open(f"{base_s3_path}/scraped_index.csv", "w") as f:
            df.to_csv(f, index=False)

    return df