import json
import time
from datetime import date, datetime
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Pastikan imports ini sesuai dengan file config Anda
from src.utils.config import OWM_API_KEY, LAT, LON, UNITS
from src.utils.paths import ensure_dir, part_dir


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
    # 1. Tentukan Koordinat (Prioritas: Input App > Default .env)
    target_lat = lat if lat is not None else LAT
    target_lon = lon if lon is not None else LON

    if not OWM_API_KEY:
        raise RuntimeError("OWM_API_KEY belum diisi di .env")

    # 2. Siapkan Output Path
    out_dir: Path = ensure_dir(part_dir("bronze", "weather_raw", d))
    out_path: Path = out_dir / "weather.json"

    # CATATAN: Fitur cache dimatikan dulu agar ganti kota berfungsi realtime.
    # Jika ingin hemat API call saat development, bisa di-uncomment.
    # if out_path.exists() and out_path.stat().st_size > 100:
    #     return str(out_path)

    sess = _session()
    last_err = None
    payload = None

    print(f"🌍 Mengambil cuaca untuk koordinat: {target_lat}, {target_lon}")

    # 3. Strategi: Coba One Call 3.0 -> Fallback ke Weather 2.5
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
                # Metadata tambahan untuk tracking
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

    # 4. FALLBACK DATA DUMMY (Penting agar demo tidak crash saat internet mati)
    if payload is None:
        print("⚠️ Semua koneksi gagal. Menggunakan DATA DUMMY (Safe Mode).")
        payload = {
            "_meta": {
                "fetched_at": datetime.utcnow().isoformat() + "Z",
                "source_url": None,
                "note": "fallback: koneksi gagal total.",
                "error": last_err,
            },
            # Struktur OneCall (biasanya dipakai logic utama)
            "current": {
                "temp": 30.5,       # Dummy Suhu
                "humidity": 75,     # Dummy Kelembapan
                "uvi": 6.5,         # Dummy UV Index
                "weather": [{"main": "Clouds", "description": "Offline Clouds"}],
            },
            # Struktur Weather 2.5 (untuk jaga-jaga)
            "main": {"temp": 30.5, "humidity": 75},
            "weather": [{"main": "Clouds"}],
            "coord": {"lat": target_lat, "lon": target_lon}
        }

    # 5. Simpan ke JSON
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    return str(out_path)