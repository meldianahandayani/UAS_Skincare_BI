import streamlit as st
import json
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import date, datetime, timedelta
from pathlib import Path
import time
import os
import requests
from bs4 import BeautifulSoup

from src.pipeline import run_all
from src.utils.config import DB_URL, OWM_API_KEY

# =========================================================
# 1. KONFIGURASI HALAMAN & CSS
# =========================================================
st.set_page_config(
    page_title="Skincare Tracker",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Daftar Kota Utama (Cache Koordinat) untuk performa
MAJOR_CITIES_COORDS = {
    "Jakarta": {"lat": -6.2088, "lon": 106.8456},
    "Surabaya": {"lat": -7.2575, "lon": 112.7521},
    "Bandung": {"lat": -6.9175, "lon": 107.6191},
    "Medan": {"lat": 3.5952, "lon": 98.6722},
    "Semarang": {"lat": -6.9667, "lon": 110.4167},
    "Makassar": {"lat": -5.1477, "lon": 119.4328},
    "Palembang": {"lat": -2.9761, "lon": 104.7754},
    "Denpasar": {"lat": -8.6705, "lon": 115.2126},
    "Banjarmasin": {"lat": -3.3194, "lon": 114.5908},
    "Yogyakarta": {"lat": -7.7955, "lon": 110.3695},
}

# Daftar Lengkap Kota di Indonesia (Sorted)
ALL_CITIES = sorted([
    "Ambon", "Balikpapan", "Banda Aceh", "Bandar Lampung", "Bandung", "Banjar", "Banjarbaru", "Banjarmasin", 
    "Batam", "Batu", "Bau-Bau", "Bekasi", "Bengkulu", "Bima", "Binjai", "Bitung", "Blitar", "Bogor", 
    "Bontang", "Bukittinggi", "Cilegon", "Cimahi", "Cirebon", "Denpasar", "Depok", "Dumai", "Gorontalo", 
    "Gunungsitoli", "Jakarta", "Jambi", "Jayapura", "Kediri", "Kendari", "Kotamobagu", "Kupang", 
    "Langsa", "Lhokseumawe", "Lubuklinggau", "Madiun", "Magelang", "Makassar", "Malang", "Manado", 
    "Mataram", "Medan", "Metro", "Mojokerto", "Padang", "Padang Panjang", "Padang Sidempuan", 
    "Pagar Alam", "Palangka Raya", "Palembang", "Palopo", "Palu", "Pangkal Pinang", "Parepare", 
    "Pariaman", "Pasuruan", "Payakumbuh", "Pekalongan", "Pekanbaru", "Pematangsiantar", "Pontianak", 
    "Prabumulih", "Probolinggo", "Sabang", "Salatiga", "Samarinda", "Sawahlunto", "Semarang", "Serang", 
    "Sibolga", "Singkawang", "Solok", "Sorong", "Subulussalam", "Sukabumi", "Sungai Penuh", "Surabaya", 
    "Surakarta", "Tangerang", "Tangerang Selatan", "Tanjung Pinang", "Tanjungbalai", "Tarakan", 
    "Tasikmalaya", "Tebing Tinggi", "Tegal", "Ternate", "Tidore Kepulauan", "Tomohon", "Tual", 
    "Yogyakarta"
])

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        color: #334155;
    }

    .stApp {
        background-color: #F8FAFC;
    }

    section[data-testid="stSidebar"] {
        background-color: #FFFFFF;
        border-right: 1px solid #E2E8F0;
    }

    h1, h2, h3 {
        color: #be185d;
        font-weight: 700 !important;
    }

    .glass-card {
        background: white;
        padding: 24px;
        border-radius: 16px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        border: 1px solid #F1F5F9;
        margin-bottom: 20px;
    }
    
    .kpi-container {
        display: flex;
        flex-direction: column;
        align-items: flex-start;
    }
    .kpi-label {
        font-size: 0.85rem;
        font-weight: 600;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .kpi-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #334155;
        margin-top: 4px;
    }
    .kpi-sub {
        font-size: 0.8rem;
        color: #64748b;
        margin-top: 4px;
    }

    .proto-card {
        height: 250px;
        overflow-y: auto;
        background: white;
        padding: 24px;
        border-radius: 16px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        border: 1px solid #F1F5F9;
        display: flex;
        flex-direction: column;
    }
    .proto-card::-webkit-scrollbar { width: 6px; }
    .proto-card::-webkit-scrollbar-thumb { background-color: #cbd5e1; border-radius: 4px; }

    div.stButton > button {
        background-color: #ec4899;
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: 600;
        padding: 0.6rem 1.2rem;
    }
    div.stButton > button:hover {
        background-color: #db2777;
        box-shadow: 0 4px 12px rgba(236, 72, 153, 0.3);
    }

    /* Enhanced visual elements */
    .safety-alert {
        background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%);
        border: 2px solid #f87171;
        border-radius: 12px;
        padding: 16px;
        margin: 10px 0;
    }
    
    .safe-alert {
        background: linear-gradient(135deg, #dcfce7 0%, #bbf7d0 100%);
        border: 2px solid #4ade80;
        border-radius: 12px;
        padding: 16px;
        margin: 10px 0;
    }
    
    .warning-alert {
        background: linear-gradient(135deg, #fef9c3 0%, #fde047 100%);
        border: 2px solid #facc15;
        border-radius: 12px;
        padding: 16px;
        margin: 10px 0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# =========================================================
# 2. DEFINISI FUNGSI
# =========================================================
def get_engine():
    if not DB_URL:
        print("⚠️ Warning: DB_URL is missing in .env file")
        return None
    try: return create_engine(DB_URL)
    except Exception as e:
        print(f"❌ Database Connection Error: {e}")
        return None

def check_db_status(engine):
    if engine is None: return False
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except: return False

def update_user_city_preference(engine, city_name):
    """
    Menyimpan preferensi kota user ke database 'user_settings'.
    Data ini akan dibaca oleh Airflow untuk penjadwalan otomatis.
    """
    if engine is None: return
    try:
        # 1. Pastikan tabel ada
        create_table_sql = text("""
            CREATE TABLE IF NOT EXISTS user_settings (
                setting_key VARCHAR(50) PRIMARY KEY,
                setting_value TEXT,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # 2. Upsert (Insert or Update) preference
        upsert_sql = text("""
            INSERT INTO user_settings (setting_key, setting_value, last_updated)
            VALUES ('current_city', :city, NOW())
            ON CONFLICT (setting_key) 
            DO UPDATE SET setting_value = EXCLUDED.setting_value, last_updated = NOW();
        """)
        
        with engine.begin() as conn:
            conn.execute(create_table_sql)
            conn.execute(upsert_sql, {"city": city_name})
            
    except Exception as e:
        print(f"⚠️ Gagal menyimpan preferensi lokasi ke DB: {e}")

def read_inventory(engine) -> pd.DataFrame:
    try:
        return pd.read_sql("SELECT * FROM inventory_skincare ORDER BY nama_produk;", engine)
    except:
        return pd.DataFrame()

def add_inventory(engine, **kwargs):
    q = text("""
        INSERT INTO inventory_skincare 
        (nama_produk, kategori, tanggal_beli, tanggal_buka, pao_bulan, tanggal_kadaluwarsa, catatan)
        VALUES (:nama_produk, :kategori, :tanggal_beli, :tanggal_buka, :pao_bulan, :tanggal_kadaluwarsa, :catatan)
    """)
    try:
        with engine.begin() as conn: conn.execute(q, kwargs)
    except Exception as e:
        # Auto-fix: Add missing column 'catatan' if it doesn't exist
        if 'column "catatan" of relation "inventory_skincare" does not exist' in str(e):
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE inventory_skincare ADD COLUMN IF NOT EXISTS catatan TEXT"))
            with engine.begin() as conn: conn.execute(q, kwargs)
        else:
            raise e

def delete_inventory(engine, id_produk: int):
    with engine.begin() as conn: conn.execute(text("DELETE FROM inventory_skincare WHERE id_produk = :id"), {"id": id_produk})

def safe_read_parquet(p: Path) -> pd.DataFrame:
    try: return pd.read_parquet(p) if p.exists() else pd.DataFrame()
    except: return pd.DataFrame()

def get_data_paths(d: date):
    base = Path("datalake")
    return {
        "gold_ctx": base / "gold" / "daily_context" / f"date={d}" / "daily_context.parquet",
        "gold_rec": base / "gold" / "recommendation" / f"date={d}" / "recommendation.parquet",
        "silver_inv": base / "silver" / "inventory" / f"date={d}" / "inventory.parquet",
        "silver_trk": base / "silver" / "tracker" / f"date={d}" / "tracker.parquet",
        "silver_wth": base / "silver" / "weather" / f"date={d}" / "weather.parquet",
        "silver_ing": base / "silver" / "ingredients" / f"date={d}" / "ingredients.parquet",
    }

def resolve_coords(city: str):
    if not OWM_API_KEY: return None
    try:
        url = f"http://api.openweathermap.org/geo/1.0/direct?q={city},ID&limit=1&appid={OWM_API_KEY}"
        r = requests.get(url, timeout=5)
        if r.status_code == 200 and r.json():
            d = r.json()[0]
            return {"lat": d["lat"], "lon": d["lon"]}
    except: return None
    return None

def get_ip_info():
    try:
        r = requests.get("http://ip-api.com/json/", timeout=5)
        if r.status_code == 200:
            return r.json()
    except: return None
    return None

def sync_journal_to_gsheets(df: pd.DataFrame):
    try:
        from streamlit_gsheets import GSheetsConnection
        if "connections" not in st.secrets or "gsheets" not in st.secrets["connections"]:
            return False, "Secrets not configured"
            
        conn = st.connection("gsheets", type=GSheetsConnection)
        worksheet = "Skincare_Journal"
        conn.update(worksheet=worksheet, data=df)
        return True, "Synced to Google Sheets"
    except ImportError:
        return False, "Library streamlit-gsheets missing"
    except Exception as e:
        return False, str(e)

def load_journal_data():
    df = pd.DataFrame()
    try:
        from streamlit_gsheets import GSheetsConnection
        if "connections" in st.secrets and "gsheets" in st.secrets["connections"]:
            conn = st.connection("gsheets", type=GSheetsConnection)
            df = conn.read(worksheet="Skincare_Journal", ttl=0)
    except: pass

    if df.empty and Path("journal_history.csv").exists():
        try: df = pd.read_csv("journal_history.csv")
        except: pass
    return df

def detect_conflicts(selected: list[str], ingredients_df: pd.DataFrame):
    from src.recommend.rules import detect_conflicts_enhanced
    conflicts, warnings = detect_conflicts_enhanced(selected, ingredients_df)
    scrape_notes = [f"ℹ️ {w}" for w in warnings]
    return conflicts, scrape_notes

def search_cosdna(keyword):
    search_url = f"https://cosdna.com/eng/product.php?q={keyword}"
    headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://cosdna.com/"}
    try:
        page = requests.get(search_url, headers=headers, timeout=10)
        soup = BeautifulSoup(page.content, "html.parser")
        all_links = soup.find_all("a", href=True)
        hasil = []
        seen = set()
        for link in all_links:
            href = link['href']
            nama = link.text.strip()
            if "cosmetic_" in href and len(nama) > 2:
                clean_url = href if "http" in href else f"https://cosdna.com/eng/{href.split('/')[-1]}"
                if clean_url not in seen:
                    hasil.append({"label": nama, "url": clean_url})
                    seen.add(clean_url)
            if len(hasil) >= 20: break
        return hasil
    except: return []

def scrape_cosdna_ingredients(url):
    headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://cosdna.com/"}
    try:
        page = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(page.content, "html.parser")
        ingredients = []
        rows = soup.find_all("tr", class_="iStuff")
        if not rows: rows = soup.find_all("tr")
        
        for tr in rows:
            tds = tr.find_all("td")
            if len(tds) >= 1:
                ing = tds[0].text.strip()
                if ing and "Ingredient" not in ing and len(ing) > 1: ingredients.append(ing)
        return ", ".join(ingredients)
    except: return ""

def scrape_cosdna_detailed(url):
    headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://cosdna.com/"}
    try:
        page = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(page.content, "html.parser")
        data = []
        rows = soup.find_all("tr", class_="iStuff")
        if not rows: rows = soup.find_all("tr")
        
        for tr in rows:
            tds = tr.find_all("td")
            if len(tds) >= 4:
                name = tds[0].text.strip()
                func = tds[1].text.strip()
                acne_str = tds[2].text.strip()
                irritant_str = tds[3].text.strip()
                
                if name and "Ingredient" not in name:
                    try: acne = int(float(acne_str)) if acne_str else 0
                    except: acne = 0
                    try: irritant = int(float(irritant_str)) if irritant_str else 0
                    except: irritant = 0
                    
                    func_clean = _clean_function_description(func)
                    data.append({
                        "Ingredient": name,
                        "Function": func_clean,
                        "Acne": acne,
                        "Irritant": irritant
                    })
        return data
    except: return []

def _clean_function_description(func_text):
    if not func_text: return "Unknown"
    import re
    func_clean = re.sub(r'<[^>]+>', '', func_text).strip()
    return func_clean if len(func_clean) > 0 else "Unknown"

# =========================================================
# 3. SIDEBAR (LOGIKA DINAMIS & AIRFLOW)
# =========================================================
with st.sidebar:
    st.markdown("<h2 style='color:#ec4899; margin-bottom:0;'>✨ Skincare Tracker</h2>", unsafe_allow_html=True)
    st.caption("Personalized Dermatology Assistant")
    st.markdown("---")
    
    nav = st.radio(
        "Menu",
        ["Dashboard", "Journal & Check", "Inventory", "Ingredient Scanner", "Data Export"],
        label_visibility="collapsed"
    )
    
    st.markdown("---")
    st.markdown("**📍 Location Settings**")
    
    # 1. Koneksi DB untuk menyimpan preferensi
    engine = get_engine()
    
    # 2. Dropdown Kota
    city_options = ALL_CITIES + ["Lainnya (Cari Manual)"]
    current_city_state = st.session_state.get("last_city", "Banjarmasin")
    
    try: def_idx = city_options.index(current_city_state)
    except: def_idx = 0
    
    selected_option = st.selectbox("Pilih Kota (Ketik untuk cari):", city_options, index=def_idx)
    
    if selected_option == "Lainnya (Cari Manual)":
        selected_city_name = st.text_input("Masukkan Nama Kota:", current_city_state)
        selected_coords = None 
    else:
        selected_city_name = selected_option
        selected_coords = MAJOR_CITIES_COORDS.get(selected_city_name)
    
    # 3. Logic Auto-Save Preferensi untuk Airflow
    # Jika user mengganti kota, simpan ke DB agar Airflow besok pagi scrape kota ini
    if "prev_selected_city" not in st.session_state:
        st.session_state["prev_selected_city"] = selected_city_name

    if selected_city_name != st.session_state["prev_selected_city"]:
        if engine:
            update_user_city_preference(engine, selected_city_name)
            st.toast(f"✅ Lokasi disimpan. Airflow akan memantau: {selected_city_name}", icon="💾")
        st.session_state["prev_selected_city"] = selected_city_name

    # 4. Tombol Deteksi Otomatis
    if st.button("📍 Deteksi Lokasi Otomatis", help="Gunakan lokasi IP Address saat ini"):
        with st.spinner("Mendeteksi lokasi..."):
            ip_data = get_ip_info()
            if ip_data and ip_data.get("status") == "success":
                d_city = ip_data.get("city", "Unknown")
                d_lat = ip_data.get("lat")
                d_lon = ip_data.get("lon")
                
                run_all(lat=d_lat, lon=d_lon)
                
                # Simpan juga hasil deteksi otomatis ke DB
                if engine: update_user_city_preference(engine, d_city)
                
                st.session_state["pipeline_run"] = datetime.now()
                st.session_state["last_city"] = d_city
                st.success(f"Lokasi ditemukan: {d_city}")
                time.sleep(1)
                st.rerun()
            else:
                st.error("Gagal mendeteksi lokasi otomatis.")

    st.markdown("---")
    st.markdown("**System Controls**")
    
    # 5. Tombol Sync Manual (On-Demand)
    if st.button("🔄 Sync Data Pipeline", width='stretch', help="Tekan jika butuh data cuaca detik ini juga"):
        if not selected_coords:
            with st.spinner(f"Mencari lokasi '{selected_city_name}'..."):
                selected_coords = resolve_coords(selected_city_name)
                if not selected_coords:
                    st.error(f"❌ Lokasi tidak ditemukan: {selected_city_name}")
                    st.stop()

        with st.spinner(f"Updating weather for {selected_city_name}..."):
            res = run_all(lat=selected_coords["lat"], lon=selected_coords["lon"])
        
        st.session_state["pipeline_run"] = datetime.now()
        st.session_state["last_city"] = selected_city_name
        st.success(f"Synced for {selected_city_name} ✅")
        st.rerun()
        
    db_status = "🟢 Connected" if check_db_status(engine) else "🔴 Disconnected"
    st.markdown(f"<div style='font-size:0.8rem; color:#94a3b8; margin-top:10px;'>Database: {db_status}</div>", unsafe_allow_html=True)

    # 6. Status Monitor Airflow (NEW)
    st.markdown("---")
    st.caption("🤖 **Auto-Scheduler Status:**")
    try:
        # Cek kapan terakhir data cuaca diperbarui oleh siapapun (User/Airflow)
        fpath = "datalake/silver/weather/weather.parquet"
        if os.path.exists(fpath):
            ts = os.path.getmtime(fpath)
            dt = datetime.fromtimestamp(ts)
            st.caption(f"Last Data Update: {dt.strftime('%H:%M %d/%m/%Y')}")
        else:
            st.caption("Belum ada data.")
    except: pass

# =========================================================
# 4. LOAD DATA UTAMA
# =========================================================
today = date.today()
paths = get_data_paths(today)
df_ctx = safe_read_parquet(paths["gold_ctx"])
df_rec = safe_read_parquet(paths["gold_rec"])
df_wth = safe_read_parquet(paths["silver_wth"])
df_trk = safe_read_parquet(paths["silver_trk"])
df_ing = safe_read_parquet(paths["silver_ing"])
df_inv_sql = read_inventory(engine) if engine else pd.DataFrame()

# Initialize weather variables globally
w_temp_now = df_wth.iloc[0]['temp_c'] if not df_wth.empty else 0
w_hum_now = df_wth.iloc[0]['humidity'] if not df_wth.empty else 0
w_uv_now = df_wth.iloc[0]['uvi'] if not df_wth.empty else 0

has_daily_stats = not df_wth.empty and 'daily_uvi_max' in df_wth.columns
w_temp_avg = df_wth.iloc[0]['daily_temp_avg'] if has_daily_stats else 0
w_hum_avg = df_wth.iloc[0]['daily_hum_avg'] if has_daily_stats else 0
w_uv_max = df_wth.iloc[0]['daily_uvi_max'] if has_daily_stats else 0

w_uv_am = df_wth.iloc[0]['am_uvi_avg'] if has_daily_stats else w_uv_now
w_hum_am = df_wth.iloc[0]['am_hum_avg'] if has_daily_stats else w_hum_now
w_hum_pm = df_wth.iloc[0]['pm_hum_avg'] if has_daily_stats else w_hum_now

# =========================================================
# 5. KONTEN HALAMAN UTAMA
# =========================================================
if nav == "Dashboard":
    col_l, col_r = st.columns([3, 1])
    with col_l:
        st.markdown(f"### 👋 Hello, User")
        st.markdown(f"Skin environment analysis for **{today.strftime('%A, %d %B %Y')}**")
    with col_r:
        current_city = st.session_state.get("last_city", "Banjarmasin")
        st.markdown(f"<div style='text-align:right; font-weight:600; color:#ec4899;'>📍 {current_city}, ID</div>", unsafe_allow_html=True)
    
    st.markdown("---")
    
    if current_city.lower() != selected_city_name.lower():
        st.warning(f"⚠️ Data yang ditampilkan adalah untuk **{current_city}**. Airflow akan memperbarui data **{selected_city_name}** pada jadwal berikutnya, atau klik **'Sync Data Pipeline'** untuk update manual sekarang.")

    c1, c2, c3, c4 = st.columns(4)
    def card(col, label, val, sub):
        col.markdown(f"""
        <div class="glass-card kpi-container">
            <span class="kpi-label">{label}</span>
            <span class="kpi-value">{val}</span>
            <span class="kpi-sub">{sub}</span>
        </div>
        """, unsafe_allow_html=True)

    sub_uv = f"Max: {w_uv_max:.1f}" if has_daily_stats else "Realtime Data"
    sub_hum = f"Avg: {w_hum_avg:.0f}%" if has_daily_stats else "Realtime Data"
    sub_temp = f"Avg: {w_temp_avg:.1f}°C" if has_daily_stats else "Realtime Data"

    card(c1, "UV Index", f"{w_uv_now:.1f}", sub_uv)
    card(c2, "Humidity", f"{w_hum_now:.0f}%", sub_hum)
    card(c3, "Temperature", f"{w_temp_now:.1f}°C", sub_temp)
    card(c4, "Skin Log", f"{len(df_trk)} Days", "Data Points")
    
    if not df_inv_sql.empty:
        chk = df_inv_sql.copy()
        chk["expiry_date"] = pd.to_datetime(chk["tanggal_kadaluwarsa"], errors='coerce')
        chk["open_date"] = pd.to_datetime(chk["tanggal_buka"], errors='coerce')
        chk["pao_days"] = chk["pao_bulan"].fillna(12) * 30
        pao_exp = chk["open_date"] + pd.to_timedelta(chk["pao_days"], unit='D')
        chk["effective_expiry"] = pd.concat([chk["expiry_date"], pao_exp], axis=1).min(axis=1)
        
        now_ts = pd.Timestamp(today)
        expired_list = chk[chk["effective_expiry"] < now_ts]
        soon_list = chk[(chk["effective_expiry"] >= now_ts) & ((chk["effective_expiry"] - now_ts).dt.days <= 30)]
        
        if not expired_list.empty:
            st.error(f"🚨 **EXPIRED ALERT**: {len(expired_list)} product(s) have expired! ({', '.join(expired_list['nama_produk'].iloc[:3])}{'...' if len(expired_list)>3 else ''}) Remove expired product from active inventory.")
        if not soon_list.empty:
            soon_list = soon_list.sort_values("effective_expiry")
            items = []
            for _, row in soon_list.iloc[:3].iterrows():
                d_left = (row['effective_expiry'] - now_ts).days
                items.append(f"{row['nama_produk']} ({d_left} days)")
            st.warning(f"⏳ **EXPIRY WARNING**: {len(soon_list)} product(s) ({', '.join(items)}{'...' if len(soon_list)>3 else ''}) Prioritize product usage before expiry")

        has_sunscreen = chk['kategori'].str.contains('Sunscreen|SPF|Sunblock', case=False, na=False).any()
        if not has_sunscreen:
            st.warning("☀️ **Missing Essential**: Kamu belum punya **Sunscreen** di inventory! Sun protection adalah langkah terpenting skincare.")

    st.markdown("### 🧴 Daily Protocol")
    
    if df_rec.empty:
        st.warning("⚠️ Recommendation data not generated. Please run the Sync Pipeline.")
    else:
        rec = df_rec.iloc[0]
        am_plan = rec.get('am_plan', '-')
        pm_plan = rec.get('pm_plan', '-')
        warnings_raw = rec.get('warnings', '')

        cA, cB = st.columns(2)
        with cA:
            st.markdown(f"""
            <div class="proto-card" style="border-left: 5px solid #f472b6;">
                <div>
                    <h3 style="margin-top:0; color:#be185d;">☀️ Day Routine</h3>
                    <p style="color:#64748b; font-size:0.9rem;">Focus: Protection & Prevention</p>
                    <hr style="border-top: 1px dashed #cbd5e1; margin: 15px 0;">
                    <p style="color:#334155; line-height:1.6;">{am_plan}</p>
                </div>
            </div>
            """, unsafe_allow_html=True)

        with cB:
            st.markdown(f"""
            <div class="proto-card" style="border-left: 5px solid #818cf8;">
                <div>
                    <h3 style="margin-top:0; color:#4f46e5;">🌙 Night Routine</h3>
                    <p style="color:#64748b; font-size:0.9rem;">Focus: Repair & Treatment</p>
                    <hr style="border-top: 1px dashed #cbd5e1; margin: 15px 0;">
                    <p style="color:#334155; line-height:1.6;">{pm_plan}</p>
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)

        if warnings_raw:
            clean_raw = warnings_raw.replace("Catatan ingredients:", "").replace("Peringatan:", "")
            items = [x.strip() for x in clean_raw.split("|") if x.strip()]
            unique_warnings = list(dict.fromkeys(items))
            
            html_alert = """
            <div style="background-color:#fee2e2; border:1px solid #fecaca; border-radius:12px; padding:16px;">
                <div style="display:flex; align-items:center; gap:8px; margin-bottom:8px;">
                    <span style="font-size:1.2rem;">⚠️</span>
                    <h4 style="color:#991b1b; margin:0; font-size:1rem;">Contraindication Alert</h4>
                </div>
                <ul style="margin-bottom:0; padding-left:20px; color:#7f1d1d;">
            """
            if unique_warnings:
                for item in unique_warnings:
                    html_alert += f"<li style='margin-bottom:4px; font-size:0.9rem;'>{item}</li>"
            html_alert += "</ul></div>"
            st.markdown(html_alert, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="background-color:#f0fdf4; border:1px solid #bbf7d0; border-radius:12px; padding:16px; display:flex; align-items:center; gap:10px;">
                <span style="font-size:1.5rem;">✅</span>
                <div>
                    <h4 style="color:#166534; margin:0; font-size:1rem;">All Clear</h4>
                    <span style="color:#15803d; font-size:0.9rem;">No product conflicts or risks detected.</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

elif nav == "Journal & Check":
    st.markdown("### 📝 Daily Journal & Safety Check")
    
    tab1, tab2 = st.tabs(["🧪 Routine Conflict Checker", "📊 Skin Tracker History"])
    
    with tab1:
        st.markdown("#### Real-time Compatibility Check")
        st.caption("Select products for your Day and Night routines to check for conflicts.")
        
        if "journal_data" not in st.session_state:
            st.session_state["journal_data"] = pd.DataFrame(columns=["Date", "Day Products", "Night Products", "Status"])
            df_sheets = load_journal_data()
            if not df_sheets.empty:
                st.session_state["journal_data"] = df_sheets
        
        if df_inv_sql.empty:
            st.info("Inventory is empty. Please add products in the Inventory menu.")
        else:
            options = df_inv_sql["nama_produk"].tolist()
            c_date = st.date_input("Date", date.today())
            col_am, col_pm = st.columns(2)
            
            with col_am:
                st.markdown("### ☀️ Day Routine")
                selected_am = st.multiselect("Select Day Products:", options, key="ms_am")
                conflicts_am, warnings_am = [], []
                if selected_am:
                    conflicts_am, warnings_am = detect_conflicts(selected_am, df_ing)

            with col_pm:
                st.markdown("### 🌙 Night Routine")
                selected_pm = st.multiselect("Select Night Products:", options, key="ms_pm")
                conflicts_pm, warnings_pm = [], []
                if selected_pm:
                    conflicts_pm, warnings_pm = detect_conflicts(selected_pm, df_ing)

            final_warn_am, final_warn_pm, cross_warn, daily_warnings = [], [], [], []

            if selected_am or selected_pm:
                st.markdown("---")
                st.markdown("### 🛡️ Safety Analysis Report")
                
                from src.recommend.rules import analyze_daily_safety
                am_has_sunscreen = False
                if not df_inv_sql.empty and selected_am:
                    cats = df_inv_sql[df_inv_sql['nama_produk'].isin(selected_am)]['kategori'].str.lower()
                    if cats.str.contains('sunscreen').any(): am_has_sunscreen = True
                    if not am_has_sunscreen:
                        am_has_sunscreen = any(x in " ".join(selected_am).lower() for x in ['sunscreen', 'spf', 'sunblock', 'uv'])
                
                daily_warnings = analyze_daily_safety(
                    selected_am, selected_pm, w_uv_am, w_hum_am, w_hum_pm, df_ing, am_has_sunscreen
                )
                
                def check_actives(products, df):
                    text = " ".join(products).lower()
                    if not df.empty:
                        rel = df[df['nama_produk'].isin(products)]
                        if not rel.empty and 'ingredients_list' in rel.columns:
                            text += " " + " ".join(rel['ingredients_list'].fillna("").astype(str).tolist()).lower()
                    r_kw = ["retinol", "retinyl", "tretinoin", "adapalene"]
                    e_kw = ["aha", "bha", "glycolic", "salicylic", "lactic", "acid"]
                    return any(k in text for k in r_kw), any(k in text for k in e_kw)

                am_ret, am_exfo = check_actives(selected_am, df_ing)
                pm_ret, pm_exfo = check_actives(selected_pm, df_ing)
                
                am_weather_warn = []
                if selected_am and not am_has_sunscreen:
                    am_weather_warn.append("⚠️ **Missing Sunscreen**: Daily sun protection is highly recommended.")
                if w_uv_am >= 3:
                    if am_ret: am_weather_warn.append("☀️ **High UV**: Retinol increases sun sensitivity. Strict SPF required.")
                    if am_exfo: am_weather_warn.append("☀️ **High UV**: Exfoliants increase sun sensitivity. Strict SPF required.")
                if w_hum_am < 50 and am_exfo:
                    am_weather_warn.append("💧 **Low Humidity**: Exfoliating in dry weather may cause irritation.")
                
                final_warn_am = [w for w in (warnings_am + am_weather_warn) if "✅" not in w]
                
                st.markdown(f"**☀️ Day Routine** (Avg UV: {w_uv_am:.1f}, Avg Hum: {w_hum_am:.0f}%)")
                if conflicts_am:
                    st.markdown(f"""<div class="safety-alert"><h5 style="color:#b91c1c; margin:0;">⛔ Day Conflicts</h5><ul style="margin-bottom:0; color:#7f1d1d; padding-left:20px;">{''.join(f'<li>{c}</li>' for c in conflicts_am)}</ul></div>""", unsafe_allow_html=True)
                if final_warn_am:
                    st.markdown(f"""<div class="warning-alert"><h5 style="color:#a16207; margin:0;">⚠️ Day Warnings</h5><ul style="margin-bottom:0; color:#78350f; padding-left:20px;">{''.join(f'<li>{w}</li>' for w in final_warn_am)}</ul></div>""", unsafe_allow_html=True)
                if not conflicts_am and not final_warn_am and selected_am:
                    st.markdown(f"""<div class="safe-alert"><h5 style="color:#15803d; margin:0;">✅ Day Safe</h5></div>""", unsafe_allow_html=True)

                pm_weather_warn = []
                if w_hum_pm < 50 and pm_exfo:
                    pm_weather_warn.append("💧 **Low Humidity**: Exfoliating in dry air may cause dryness.")
                
                final_warn_pm = [w for w in (warnings_pm + pm_weather_warn) if "✅" not in w]
                
                st.markdown(f"**🌙 Night Routine** (Avg Hum: {w_hum_pm:.0f}%)")
                if conflicts_pm:
                    st.markdown(f"""<div class="safety-alert"><h5 style="color:#b91c1c; margin:0;">⛔ Night Conflicts</h5><ul style="margin-bottom:0; color:#7f1d1d; padding-left:20px;">{''.join(f'<li>{c}</li>' for c in conflicts_pm)}</ul></div>""", unsafe_allow_html=True)
                if final_warn_pm:
                    st.markdown(f"""<div class="warning-alert"><h5 style="color:#a16207; margin:0;">⚠️ Night Warnings</h5><ul style="margin-bottom:0; color:#78350f; padding-left:20px;">{''.join(f'<li>{w}</li>' for w in final_warn_pm)}</ul></div>""", unsafe_allow_html=True)
                if not conflicts_pm and not final_warn_pm and selected_pm:
                    st.markdown(f"""<div class="safe-alert"><h5 style="color:#15803d; margin:0;">✅ Night Safe</h5></div>""", unsafe_allow_html=True)

                cross_warn = []
                if (am_ret or pm_ret) and (am_exfo or pm_exfo):
                    cross_warn.append("⚠️ **Over-Exfoliation Risk**: Retinol + Exfoliants in same day.")
                if am_ret and pm_ret:
                    cross_warn.append("⚠️ **High Retinol Load**: Using Retinol twice daily is harsh.")
                
                if cross_warn or daily_warnings:
                    st.markdown("**📅 Daily Interaction**")
                    all_daily = cross_warn + daily_warnings
                    st.markdown(f"""<div class="warning-alert"><h5 style="color:#a16207; margin:0;">⚠️ Cross-Routine Warnings</h5><ul style="margin-bottom:0; color:#78350f; padding-left:20px;">{''.join(f'<li>{w}</li>' for w in all_daily)}</ul></div>""", unsafe_allow_html=True)

                total_issues = len(conflicts_am) + len(conflicts_pm) + len(final_warn_am) + len(final_warn_pm) + len(cross_warn) + len(daily_warnings)
                
                st.markdown("#### 🏁 Analysis Conclusion")
                if total_issues > 0:
                      st.markdown(f"""
                      <div class="safety-alert">
                        <h5 style="color:#b91c1c; margin:0;">⚠️ Caution Recommended ({total_issues} Issues)</h5>
                        <p style="margin:0; font-size:0.9rem;">Potential conflicts or risks detected.</p>
                      </div>
                      """, unsafe_allow_html=True)
                      st.toast(f"Found {total_issues} potential issues.", icon="⚠️")
                else:
                      st.markdown("""
                      <div class="safe-alert">
                        <h5 style="color:#15803d; margin:0;">✅ Routine Approved</h5>
                        <p style="margin:0; font-size:0.9rem;">No conflicts detected.</p>
                      </div>
                      """, unsafe_allow_html=True)
                      st.toast("Routine looks perfect!", icon="✨")

            st.markdown("---")
            journal_df = st.session_state["journal_data"]
            c_date_str = c_date.strftime("%Y-%m-%d")
            if not journal_df.empty and "Date" in journal_df.columns:
                journal_df["Date"] = journal_df["Date"].astype(str)
            
            entry_exists = (journal_df["Date"] == c_date_str).any() if not journal_df.empty else False

            if st.session_state.get("confirm_overwrite") and st.session_state.get("confirm_overwrite") != c_date_str:
                st.session_state["confirm_overwrite"] = None

            trigger_save = False
            if st.session_state.get("confirm_overwrite") == c_date_str:
                st.warning(f"⚠️ Jurnal untuk tanggal {c_date_str} sudah ada. Klik tombol di bawah untuk memperbaharui.")
                col_conf1, col_conf2 = st.columns([1, 2])
                with col_conf1:
                    if st.button("🔄 Perbaharui Jurnal"):
                        trigger_save = True
                        st.session_state["confirm_overwrite"] = None
                with col_conf2:
                    if st.button("❌ Batal"):
                        st.session_state["confirm_overwrite"] = None
                        st.rerun()
            else:
                if st.button("💾 Save to Journal"):
                    if entry_exists:
                        st.session_state["confirm_overwrite"] = c_date_str
                        st.rerun()
                    else:
                        trigger_save = True

            if trigger_save:
                status_str = "✅ Safe"
                if conflicts_am or conflicts_pm: status_str = "⚠️ Conflict"
                elif final_warn_am or final_warn_pm or cross_warn: status_str = "ℹ️ Warnings"
                
                new_row = {"Date": c_date_str, "Day Products": ", ".join(selected_am), "Night Products": ", ".join(selected_pm), "Status": status_str}
                
                if entry_exists:
                    idx = journal_df[journal_df["Date"] == c_date_str].index
                    for i in idx:
                        journal_df.at[i, "Day Products"] = new_row["Day Products"]
                        journal_df.at[i, "Night Products"] = new_row["Night Products"]
                        journal_df.at[i, "Status"] = new_row["Status"]
                    st.session_state["journal_data"] = journal_df
                    msg = "Journal Updated!"
                else:
                    new_entry = pd.DataFrame([new_row])
                    st.session_state["journal_data"] = pd.concat([journal_df, new_entry], ignore_index=True)
                    msg = "Journal Entry Saved!"
                
                gs_success, gs_msg = sync_journal_to_gsheets(st.session_state["journal_data"])
                st.session_state["journal_data"].to_csv("journal_history.csv", index=False)
                
                if gs_success: st.toast(gs_msg, icon="☁️")
                else: st.toast("Saved locally (Offline)", icon="💾")
                st.success(msg)
                time.sleep(1)
                st.rerun()

            st.markdown("---")
            st.markdown("### 🚨 Breakout Detector")
            if st.checkbox("Apakah anda mengalami breakout hari ini?"):
                if st.button("🔍 Analisis Riwayat 2 Minggu"):
                    j_df = st.session_state["journal_data"].copy()
                    if not j_df.empty:
                        j_df["Date"] = pd.to_datetime(j_df["Date"], errors='coerce')
                        end_date = pd.Timestamp(date.today())
                        start_date = end_date - timedelta(days=14)
                        recent_logs = j_df.loc[(j_df["Date"] >= start_date) & (j_df["Date"] <= end_date)]
                        
                        if recent_logs.empty:
                            st.warning("Tidak ada data jurnal dalam 14 hari terakhir.")
                        else:
                            st.info(f"Menganalisis {len(recent_logs)} entri...")
                            warn_logs = recent_logs[recent_logs["Status"].astype(str).str.contains("Warning|Conflict", case=False)]
                            if not warn_logs.empty:
                                st.warning(f"⚠️ Terdeteksi {len(warn_logs)} hari berisiko:")
                                st.dataframe(warn_logs)
                            
                            used_products = set()
                            for _, r in recent_logs.iterrows():
                                d_p = [x.strip() for x in str(r.get("Day Products", "")).split(",") if x.strip()]
                                n_p = [x.strip() for x in str(r.get("Night Products", "")).split(",") if x.strip()]
                                used_products.update(d_p + n_p)
                            
                            st.markdown(f"**Produk yang dipakai ({len(used_products)}):**")
                            st.caption(", ".join(list(used_products)))
                            
                            subset_ing = df_ing[df_ing["nama_produk"].isin(used_products)]
                            if not subset_ing.empty and "detailed_analysis" in subset_ing.columns:
                                suspects_acne = []
                                for _, row in subset_ing.iterrows():
                                    try:
                                        dets = json.loads(row.get("detailed_analysis", "[]"))
                                        for d in dets:
                                            acne = int(d.get("Acne", 0))
                                            if acne >= 3:
                                                suspects_acne.append(f"{d.get('Ingredient')} ({acne}) in {row['nama_produk']}")
                                    except: pass
                                
                                if suspects_acne:
                                    st.error("🌋 **High Acne Triggers Found:**")
                                    for s in list(set(suspects_acne)): st.markdown(f"- {s}")
                                else:
                                    st.success("Tidak ditemukan pemicu acne skor tinggi.")
                            else:
                                st.warning("Data ingredients belum lengkap.")

    with tab2:
        st.markdown("### 📊 Personal Skin Tracker History")
        if not st.session_state["journal_data"].empty:
            st.dataframe(st.session_state["journal_data"], width="stretch")
            st.markdown("---")
            with st.expander("🗑️ Delete Specific Entry"):
                dates_list = st.session_state["journal_data"]["Date"].astype(str).unique().tolist()
                dates_list.sort(reverse=True)
                sel_del_date = st.selectbox("Select Date:", dates_list, key="del_date_sel")
                if st.button("Delete Selected Entry"):
                    st.session_state["journal_data"] = st.session_state["journal_data"][st.session_state["journal_data"]["Date"].astype(str) != sel_del_date]
                    st.session_state["journal_data"].to_csv("journal_history.csv", index=False)
                    sync_journal_to_gsheets(st.session_state["journal_data"])
                    st.success("Deleted!")
                    time.sleep(0.5)
                    st.rerun()
            
            csv_data = st.session_state["journal_data"].to_csv(index=False).encode('utf-8')
            st.download_button("📤 Export to CSV", csv_data, f"journal_{today}.csv", "text/csv")
        else:
            st.info("No journal entries yet.")

elif nav == "Inventory":
    st.markdown("### 📦 Digital Shelf")
    if engine is None:
        st.error("Database connection failed.")
        st.stop()
        
    tab_view, tab_add = st.tabs(["📋 View Stock", "➕ Add Product"])
    
    with tab_view:
        if df_inv_sql.empty:
            st.info("Your shelf is empty.")
        else:
            df_disp = df_inv_sql.copy()
            df_disp["expiry_date"] = pd.to_datetime(df_disp["tanggal_kadaluwarsa"], errors='coerce')
            df_disp["open_date"] = pd.to_datetime(df_disp["tanggal_buka"], errors='coerce')
            df_disp["today"] = pd.to_datetime(today)
            df_disp["pao_days"] = df_disp["pao_bulan"].fillna(12) * 30
            pao_expiry_calc = df_disp["open_date"] + pd.to_timedelta(df_disp["pao_days"], unit='D')
            df_disp["pao_expiry"] = pd.concat([pao_expiry_calc, df_disp["expiry_date"]], axis=1).min(axis=1)
            df_disp["pao_expiry_display"] = df_disp["pao_expiry"].dt.date
            
            def get_status(row):
                now, exp, pao = row["today"], row["expiry_date"], row["pao_expiry"]
                if pd.notnull(exp) and now >= exp: return "❌ Expired"
                if pd.notnull(pao) and now >= pao: return "❌ PAO Exceeded"
                if pd.notnull(exp) and 0 <= (exp - now).days <= 30: return "⚠️ Expiring Soon"
                return "✅ Good"
            
            df_disp["Status"] = df_disp.apply(get_status, axis=1)
            if "catatan" not in df_disp.columns: df_disp["catatan"] = ""

            st.dataframe(
                df_disp,
                column_config={
                    "nama_produk": "Product", "kategori": "Category", "pao_bulan": "PAO (Mo)",
                    "tanggal_kadaluwarsa": st.column_config.DateColumn("Expiry"),
                    "pao_expiry_display": st.column_config.DateColumn("PAO End"),
                    "Status": "Condition", "catatan": "Notes"
                },
                column_order=["nama_produk", "kategori", "pao_bulan", "tanggal_kadaluwarsa", "pao_expiry_display", "Status", "catatan"],
                width="stretch", height=500
            )
            
            with st.expander("🗑️ Remove Product"):
                to_del = st.selectbox("Select product:", df_inv_sql["id_produk"].astype(str) + " - " + df_inv_sql["nama_produk"])
                if st.button("Delete Permanently"):
                    pid = int(to_del.split(" - ")[0])
                    delete_inventory(engine, pid)
                    st.success("Product removed.")
                    st.rerun()

    with tab_add:
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        st.markdown("#### 🔍 Search & Add")
        col_s1, col_s2 = st.columns([3, 1])
        search_kw = col_s1.text_input("Search Product Name", key="search_cosdna_input")
        if col_s2.button("Search", key="btn_search_cosdna"):
            if search_kw:
                with st.spinner("Searching..."):
                    results = search_cosdna(search_kw)
                    st.session_state["cosdna_results"] = results
                    if not results: st.warning("No results found.")
        
        if "cosdna_results" in st.session_state and st.session_state["cosdna_results"]:
            options = {x["label"]: x for x in st.session_state["cosdna_results"]}
            selected_label = st.selectbox("Select Product:", options.keys(), key="sb_cosdna_res")
            if st.button("⬇️ Use This Product Data", key="btn_use_cosdna"):
                url = options[selected_label]['url']
                ings = scrape_cosdna_ingredients(url)
                st.session_state["form_prod"] = selected_label.strip()
                st.session_state["form_notes"] = ings
                st.rerun()
        
        st.markdown("---")
        with st.form("inventory_form"):
            prod = st.text_input("Product Name", value=st.session_state.get("form_prod", ""))
            c1, c2 = st.columns(2)
            cat = c1.selectbox("Category", ["Cleanser", "Toner", "Serum", "Moisturizer", "Sunscreen", "Exfoliant", "Mask"])
            pao = c2.number_input("PAO (Months)", 12)
            c3, c4 = st.columns(2)
            open_dt = c3.date_input("Open Date")
            exp_dt = c4.date_input("Expiry Date", value=today + timedelta(days=365))
            note = st.text_area("Notes (Ingredients)", value=st.session_state.get("form_notes", ""))
            
            if st.form_submit_button("Save to Shelf"):
                try:
                    add_inventory(engine, nama_produk=prod, kategori=cat, tanggal_beli=None,
                                  tanggal_buka=open_dt, pao_bulan=pao, tanggal_kadaluwarsa=exp_dt, catatan=note)
                    st.success("Product Added Successfully")
                    st.session_state.pop("form_prod", None)
                    st.session_state.pop("form_notes", None)
                    st.session_state.pop("cosdna_results", None)
                    time.sleep(1)
                    st.rerun()
                except Exception as e: st.error(f"Error: {e}")
        st.markdown("</div>", unsafe_allow_html=True)

elif nav == "Ingredient Scanner":
    st.markdown("### 🔎 Product Composition Analysis")
    st.caption("Powered by Web Scraping & Heuristic Analysis")
    col_scan1, col_scan2 = st.columns([3, 1])
    scan_kw = col_scan1.text_input("Enter Product Name:", key="scan_cosdna_input")
    if col_scan2.button("Search", key="btn_scan_cosdna"):
        if scan_kw:
            with st.spinner("Searching..."):
                results = search_cosdna(scan_kw)
                st.session_state["scan_results"] = results
                if not results: st.warning("No results found.")

    if "scan_results" in st.session_state and st.session_state["scan_results"]:
        options = {x["label"]: x for x in st.session_state["scan_results"]}
        selected_scan = st.selectbox("Select Product to Analyze:", options.keys(), key="sb_scan_res")
        if st.button("🔬 Analyze Ingredients", key="btn_analyze_cosdna"):
            url = options[selected_scan]['url']
            with st.spinner("Scraping & Analyzing..."):
                details = scrape_cosdna_detailed(url)
                st.session_state["scan_details"] = details

    if "scan_details" in st.session_state:
        details = st.session_state["scan_details"]
        st.markdown("---")
        st.markdown(f"### 🧬 Analysis Result: {st.session_state.get('sb_scan_res', 'Product')}")
        df_det = pd.DataFrame(details)
        if not df_det.empty:
            df_det['Acne'] = pd.to_numeric(df_det['Acne'], errors='coerce').fillna(0)
            df_det['Irritant'] = pd.to_numeric(df_det['Irritant'], errors='coerce').fillna(0)
            high_acne = df_det[df_det['Acne'] >= 3]
            high_irritant = df_det[df_det['Irritant'] >= 3]
            
            m1, m2, m3 = st.columns(3)
            m1.metric("Total Ingredients", len(df_det))
            m2.metric("Acne Triggers", len(high_acne), delta_color="inverse" if len(high_acne)>0 else "normal")
            m3.metric("Irritant Triggers", len(high_irritant), delta_color="inverse" if len(high_irritant)>0 else "normal")
            
            st.dataframe(df_det, column_config={"Acne": st.column_config.NumberColumn("Acne (0-5)"), "Irritant": st.column_config.NumberColumn("Irritant (0-5)")}, width="stretch", hide_index=True)
            
            if not high_acne.empty: st.warning(f"⚠️ **Acne Alert:** Contains {', '.join(high_acne['Ingredient'].tolist())}")
            if not high_irritant.empty: st.error(f"🔥 **Irritant Alert:** Contains {', '.join(high_irritant['Ingredient'].tolist())}")
            
            if not high_acne.empty or not high_irritant.empty:
                 st.markdown("""<div class="safety-alert"><h5 style="color:#b91c1c; margin:0;">⚠️ Caution Recommended</h5><p style="margin:0; font-size:0.9rem;">Contains high-risk ingredients.</p></div>""", unsafe_allow_html=True)
            elif (df_det['Acne'] > 0).any():
                 st.markdown("""<div class="warning-alert"><h5 style="color:#a16207; margin:0;">✨ Generally Safe</h5></div>""", unsafe_allow_html=True)
            else:
                 st.markdown("""<div class="safe-alert"><h5 style="color:#15803d; margin:0;">✅ Excellent Safety Profile</h5></div>""", unsafe_allow_html=True)
        else:
            st.info("No detailed ingredient data found.")

elif nav == "Data Export":
    st.markdown("### 📤 Data Export Center")
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    def to_csv(df): return df.to_csv(index=False).encode('utf-8')
    with c1:
        st.markdown("**Daily Context (Gold)**")
        if not df_ctx.empty: st.download_button("Download CSV", to_csv(df_ctx), "gold_context.csv", "text/csv", key="btn_ctx")
        else: st.button("No Data", disabled=True)
    with c2:
        st.markdown("**Inventory Backup (SQL)**")
        if not df_inv_sql.empty: st.download_button("Download CSV", to_csv(df_inv_sql), "inventory.csv", "text/csv", key="btn_inv")
        else: st.button("No Data", disabled=True)
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("""
<div style="text-align:center; color:#cbd5e1; padding: 20px; font-size:0.8rem;">
    Skincare Tracker • Intelligent Data Pipeline • 2025
</div>
""", unsafe_allow_html=True)