import json
import time
import os
import s3fs
from datetime import date, datetime
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.utils.config import OWM_API_KEY, LAT, LON, UNITS


def _session() -> requests.Session:
    """
    Membuat session requests yang 'tahan banting'.
    Akan mencoba ulang (retry) otomatis jika koneksi putus/timeout.
    """
    retry = Retry(
        total=3,
        backoff_factor=1.2,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        raise_on_status=False,
    )
    s = requests.Session()
    s.headers.update({"User-Agent": "Mozilla/5.0 (UAS-Skincare-Lakehouse/1.0)"})
    adapter = HTTPAdapter(max_retries=retry)
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    return s


def run(d: date, lat=None, lon=None) -> str:
    """
    Ambil data cuaca (UV, humidity, temp).
    Mendukung pilihan kota dinamis via parameter lat/lon.
    """
    target_lat = lat if lat is not None else LAT
    target_lon = lon if lon is not None else LON

    if not OWM_API_KEY:
        raise RuntimeError("OWM_API_KEY belum diisi di .env")

    sess = _session()
    last_err = None
    payload = None

    print(f"🌍 Mengambil cuaca untuk koordinat: {target_lat}, {target_lon}")

    urls = [
        ("https://api.openweathermap.org/data/3.0/onecall", {
            "lat": target_lat, "lon": target_lon, "appid": OWM_API_KEY, "units": UNITS
        }),
        ("https://api.openweathermap.org/data/2.5/weather", {
            "lat": target_lat, "lon": target_lon, "appid": OWM_API_KEY, "units": UNITS
        }),
    ]

    for url, params in urls:
        try:
            print(f"   Mencoba endpoint: {url}...")
            r = sess.get(url, params=params, timeout=20)
            
            if r.status_code == 200:
                payload = r.json()
                payload["_meta"] = {
                    "fetched_at": datetime.utcnow().isoformat() + "Z",
                    "source_url": url,
                    "coords": f"{target_lat},{target_lon}"
                }
                print("   ✅ Berhasil.")
                break
            else:
                last_err = f"HTTP {r.status_code}: {r.text[:200]}"
                print(f"   ❌ Gagal: {last_err}")
                time.sleep(0.8)
                
        except requests.RequestException as e:
            last_err = repr(e)
            print(f"   ❌ Error Koneksi: {last_err}")
            time.sleep(1.0)

    # FALLBACK DATA DUMMY 
    if payload is None:
        raise RuntimeError(f"Gagal mengambil data cuaca dari API (OpenWeatherMap). Error: {last_err}. Pastikan API Key valid dan koneksi internet stabil.")

    # MinIO Write
    is_docker = os.path.exists("/.dockerenv")
    default_host = "minio" if is_docker else "localhost"
    minio_endpoint = os.getenv("MINIO_ENDPOINT", f"http://{default_host}:9000")
    fs = s3fs.S3FileSystem(
        key=os.getenv("MINIO_ACCESS_KEY", "skincare_admin"),
        secret=os.getenv("MINIO_SECRET_KEY", "skincare_password"),
        client_kwargs={'endpoint_url': minio_endpoint}
    )

    s3_path = f"datalake/bronze/weather/date={d}/weather.json"
    with fs.open(s3_path, "w") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    
    print(f"💾 Saved weather to MinIO: s3://{s3_path}")
    return f"s3://{s3_path}"