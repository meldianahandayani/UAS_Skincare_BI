import streamlit as st
import json
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import date, datetime, timedelta
from pathlib import Path
import time
from src.pipeline import run_all
from src.utils.config import DB_URL, OWM_API_KEY
import requests
from bs4 import BeautifulSoup

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

    .badge {
        display: inline-block;
        padding: 0.25em 0.6em;
        font-size: 0.75rem;
        font-weight: 700;
        border-radius: 0.375rem;
    }
    .badge-pink { background-color: #fce7f3; color: #be185d; }
    .badge-green { background-color: #dcfce7; color: #15803d; }
    .badge-red { background-color: #fee2e2; color: #b91c1c; }
    .badge-yellow { background-color: #fef9c3; color: #a16207; }
    .badge-orange { background-color: #fed7aa; color: #c2410c; }
    
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
    
    .ingredient-card {
        background: white;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border-left: 4px solid #ec4899;
        margin: 10px 0;
    }
    
    .conflict-item {
        background: #fee2e2;
        border-left: 4px solid #dc2626;
        padding: 12px;
        margin: 8px 0;
        border-radius: 0 8px 8px 0;
    }
    
    .safe-item {
        background: #dcfce7;
        border-left: 4px solid #16a34a;
        padding: 12px;
        margin: 8px 0;
        border-radius: 0 8px 8px 0;
    }
    
    .metric-card {
        background: white;
        padding: 20px;
        border-radius: 16px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        border: 1px solid #F1F5F9;
        text-align: center;
    }
    
    .progress-bar {
        background-color: #f1f5f9;
        border-radius: 8px;
        overflow: hidden;
        height: 8px;
        margin: 8px 0;
    }
    
    .progress-fill {
        height: 100%;
        background: linear-gradient(90deg, #ec4899, #f472b6);
        transition: width 0.3s ease;
    }
    
    /* Floating action button style */
    .fab {
        position: fixed;
        bottom: 20px;
        right: 20px;
        background-color: #ec4899;
        color: white;
        border: none;
        border-radius: 50%;
        width: 56px;
        height: 56px;
        font-size: 24px;
        cursor: pointer;
        box-shadow: 0 4px 12px rgba(236, 72, 153, 0.3);
        z-index: 1000;
    }
    
    .fab:hover {
        background-color: #db2777;
        transform: scale(1.1);
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
        # Tambahkan ,ID untuk memastikan pencarian di Indonesia
        url = f"http://api.openweathermap.org/geo/1.0/direct?q={city},ID&limit=1&appid={OWM_API_KEY}"
        r = requests.get(url, timeout=5)
        if r.status_code == 200 and r.json():
            d = r.json()[0]
            return {"lat": d["lat"], "lon": d["lon"]}
    except: return None
    return None

def get_ip_info():
    try:
        # Menggunakan ip-api.com untuk deteksi lokasi via IP
        r = requests.get("http://ip-api.com/json/", timeout=5)
        if r.status_code == 200:
            return r.json()
    except: return None
    return None

def sync_journal_to_gsheets(df: pd.DataFrame):
    """
    Syncs the full journal dataframe to Google Sheets.
    Requires st.secrets["connections"]["gsheets"] to be configured.
    """
    try:
        from streamlit_gsheets import GSheetsConnection
        # Basic check to prevent errors if secrets are missing
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
    """
    Loads journal history from Google Sheets, falls back to local CSV if failed.
    """
    df = pd.DataFrame()
    # 1. Try Google Sheets
    try:
        from streamlit_gsheets import GSheetsConnection
        if "connections" in st.secrets and "gsheets" in st.secrets["connections"]:
            conn = st.connection("gsheets", type=GSheetsConnection)
            df = conn.read(worksheet="Skincare_Journal", ttl=0)
    except:
        pass

    # 2. Fallback to Local CSV if Sheets returned nothing
    if df.empty and Path("journal_history.csv").exists():
        try: df = pd.read_csv("journal_history.csv")
        except: pass
    return df

def detect_conflicts(selected: list[str], ingredients_df: pd.DataFrame):
    """
    Enhanced conflict detection using the improved rules system
    """
    from src.recommend.rules import detect_conflicts_enhanced
    
    # Use the enhanced detection system
    conflicts, warnings = detect_conflicts_enhanced(selected, ingredients_df)
    
    # Convert warnings to scrape_notes format for compatibility
    scrape_notes = [f"ℹ️ {w}" for w in warnings]
    
    return conflicts, scrape_notes

def analyze_risk_enhanced(ing_list: list[str]):
    """
    Enhanced risk analysis using the improved system
    """
    from src.recommend.rules import analyze_ingredient_safety
    
    if not ing_list:
        return [], []
    
    analysis = analyze_ingredient_safety(ing_list)
    
    comedogenic = analysis.get("comedogenic_risk", [])
    irritants = analysis.get("irritant_risk", [])
    
    return comedogenic, irritants

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
                    # Convert acne/irritant to integers safely
                    try:
                        acne = int(float(acne_str)) if acne_str else 0
                    except (ValueError, TypeError):
                        acne = 0
                    
                    try:
                        irritant = int(float(irritant_str)) if irritant_str else 0
                    except (ValueError, TypeError):
                        irritant = 0
                    
                    # Clean function description
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
    """
    Clean and standardize function descriptions for better display.
    """
    if not func_text:
        return "Unknown"
    
    # Remove HTML tags and extra whitespace
    import re
    func_clean = re.sub(r'<[^>]+>', '', func_text)
    func_clean = func_clean.strip()
    
    # Common function mappings for better readability
    function_mapping = {
        "surfactant": "Cleansing Agent",
        "emulsifier": "Emulsion Stabilizer", 
        "preservative": "Preservative",
        "fragrance": "Fragrance",
        "colorant": "Coloring Agent",
        "humectant": "Moisturizing Agent",
        "emollient": "Skin Softener",
        "solvent": "Solvent",
        "thickener": "Viscosity Control",
        "antioxidant": "Antioxidant",
        "conditioning": "Skin Conditioning",
        "buffering": "pH Adjuster",
        "chelating": "Chelating Agent",
        "denaturant": "Denaturant",
        "opacifier": "Opacifying Agent",
        "viscosity": "Viscosity Control",
        "binder": "Binding Agent",
        "abrasive": "Exfoliating Agent",
        "anticaking": "Anti-caking Agent"
    }
    
    func_lower = func_clean.lower()
    for key, value in function_mapping.items():
        if key in func_lower:
            return value
    
    # Return cleaned version if no mapping found
    return func_clean if len(func_clean) > 0 else "Unknown"

# =========================================================
# 3. SIDEBAR (Dijalankan SETELAH fungsi didefinisikan)
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
    
    # Dropdown Pilihan Kota (Searchable)
    city_options = ALL_CITIES + ["Lainnya (Cari Manual)"]
    
    # Default ke kota terakhir yang di-sync (agar tidak muncul warning mismatch saat reload)
    current_city_state = st.session_state.get("last_city", "Banjarmasin")
    
    if current_city_state in city_options:
        try: def_idx = city_options.index(current_city_state)
        except: def_idx = 0
        manual_default = "Banjarmasin"
    else:
        try: def_idx = city_options.index("Lainnya (Cari Manual)")
        except: def_idx = 0
        manual_default = current_city_state
    
    selected_option = st.selectbox("Pilih Kota (Ketik untuk cari):", city_options, index=def_idx)
    
    if selected_option == "Lainnya (Cari Manual)":
        selected_city_name = st.text_input("Masukkan Nama Kota:", manual_default)
        selected_coords = None # Akan dicari saat sync
    else:
        selected_city_name = selected_option
        # Cek cache major cities, jika tidak ada, akan dicari saat sync
        selected_coords = MAJOR_CITIES_COORDS.get(selected_city_name)
    
    if st.button("📍 Deteksi Lokasi Otomatis", help="Gunakan lokasi IP Address saat ini"):
        with st.spinner("Mendeteksi lokasi..."):
            ip_data = get_ip_info()
            if ip_data and ip_data.get("status") == "success":
                d_city = ip_data.get("city", "Unknown")
                d_lat = ip_data.get("lat")
                d_lon = ip_data.get("lon")
                
                # Jalankan pipeline langsung
                run_all(lat=d_lat, lon=d_lon)
                
                st.session_state["pipeline_run"] = datetime.now()
                st.session_state["last_city"] = d_city
                st.success(f"Lokasi ditemukan: {d_city}")
                time.sleep(1)
                st.rerun()
            else:
                st.error("Gagal mendeteksi lokasi otomatis.")

    st.markdown("---")
    st.markdown("**System Controls**")
    
    if st.button("🔄 Sync Data Pipeline", width='stretch'):
        # Jika koordinat belum ada (dari manual atau kota non-major), cari sekarang
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
        
    engine = get_engine()
    db_status = "🟢 Connected" if check_db_status(engine) else "🔴 Disconnected"
    st.markdown(f"<div style='font-size:0.8rem; color:#94a3b8; margin-top:10px;'>Database: {db_status}</div>", unsafe_allow_html=True)

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
# Realtime (Current)
w_temp_now = df_wth.iloc[0]['temp_c'] if not df_wth.empty else 0
w_hum_now = df_wth.iloc[0]['humidity'] if not df_wth.empty else 0
w_uv_now = df_wth.iloc[0]['uvi'] if not df_wth.empty else 0

# Daily Stats (if available)
has_daily_stats = not df_wth.empty and 'daily_uvi_max' in df_wth.columns
w_temp_avg = df_wth.iloc[0]['daily_temp_avg'] if has_daily_stats else 0
w_hum_avg = df_wth.iloc[0]['daily_hum_avg'] if has_daily_stats else 0
w_uv_max = df_wth.iloc[0]['daily_uvi_max'] if has_daily_stats else 0

# Variables for Safety Analysis (Use Stats if available for better context, else Realtime)
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
        st.warning(f"⚠️ Data yang ditampilkan adalah untuk **{current_city}**. Klik tombol **'Sync Data Pipeline'** di sidebar untuk memperbarui data ke **{selected_city_name}**.")


    c1, c2, c3, c4 = st.columns(4)
    def card(col, label, val, sub):
        col.markdown(f"""
        <div class="glass-card kpi-container">
            <span class="kpi-label">{label}</span>
            <span class="kpi-value">{val}</span>
            <span class="kpi-sub">{sub}</span>
        </div>
        """, unsafe_allow_html=True)

    # Sub-text logic
    sub_uv = f"Max: {w_uv_max:.1f}" if has_daily_stats else "Realtime Data"
    sub_hum = f"Avg: {w_hum_avg:.0f}%" if has_daily_stats else "Realtime Data"
    sub_temp = f"Avg: {w_temp_avg:.1f}°C" if has_daily_stats else "Realtime Data"

    card(c1, "UV Index", f"{w_uv_now:.1f}", sub_uv)
    card(c2, "Humidity", f"{w_hum_now:.0f}%", sub_hum)
    card(c3, "Temperature", f"{w_temp_now:.1f}°C", sub_temp)
    card(c4, "Skin Log", f"{len(df_trk)} Days", "Data Points")
    
    # --- EXPIRY ALERTS ---
    if not df_inv_sql.empty:
        chk = df_inv_sql.copy()
        chk["expiry_date"] = pd.to_datetime(chk["tanggal_kadaluwarsa"], errors='coerce')
        chk["open_date"] = pd.to_datetime(chk["tanggal_buka"], errors='coerce')
        chk["pao_days"] = chk["pao_bulan"].fillna(12) * 30
        
        # Calculate effective expiry (earliest of hard expiry OR opened date + PAO)
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

        # --- MISSING ESSENTIALS CHECK ---
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
        
        # Initialize session state for journal data
        if "journal_data" not in st.session_state:
            st.session_state["journal_data"] = pd.DataFrame(columns=["Date", "Day Products", "Night Products", "Status"])
            df_sheets = load_journal_data()
            if not df_sheets.empty:
                st.session_state["journal_data"] = df_sheets
            else:
                st.session_state["journal_data"] = pd.DataFrame(columns=["Date", "Day Products", "Night Products", "Status"])
        
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

            # Initialize analysis variables to avoid NameError if block is skipped
            final_warn_am, final_warn_pm, cross_warn, daily_warnings = [], [], [], []

            # --- DETAILED SAFETY ANALYSIS ---
            if selected_am or selected_pm:
                st.markdown("---")
                st.markdown("### 🛡️ Safety Analysis Report")
                
                # Calculate daily_warnings (Weather & Routine Analysis)
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
                
                # Helper for content check
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
                
                # 1. AM ANALYSIS (Day Weather)
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

                # 2. PM ANALYSIS (Night Weather - Ignore UV)
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

                # 3. CROSS ROUTINE
                cross_warn = []
                if (am_ret or pm_ret) and (am_exfo or pm_exfo):
                    cross_warn.append("⚠️ **Over-Exfoliation Risk**: Retinol + Exfoliants in same day.")
                if am_ret and pm_ret:
                    cross_warn.append("⚠️ **High Retinol Load**: Using Retinol twice daily is harsh.")
                
                if cross_warn or daily_warnings:
                    st.markdown("**📅 Daily Interaction**")
                    all_daily = cross_warn + daily_warnings
                    st.markdown(f"""<div class="warning-alert"><h5 style="color:#a16207; margin:0;">⚠️ Cross-Routine Warnings</h5><ul style="margin-bottom:0; color:#78350f; padding-left:20px;">{''.join(f'<li>{w}</li>' for w in all_daily)}</ul></div>""", unsafe_allow_html=True)

                # Toast Summary
                total_issues = len(conflicts_am) + len(conflicts_pm) + len(final_warn_am) + len(final_warn_pm) + len(cross_warn) + len(daily_warnings)
                
                st.markdown("#### 🏁 Analysis Conclusion")
                if total_issues > 0:
                     st.markdown(f"""
                     <div class="safety-alert">
                        <h5 style="color:#b91c1c; margin:0;">⚠️ Caution Recommended ({total_issues} Issues)</h5>
                        <p style="margin:0; font-size:0.9rem;">Potential conflicts or risks detected. Please review the warnings above.</p>
                     </div>
                     """, unsafe_allow_html=True)
                     st.toast(f"Found {total_issues} potential issues in your routine.", icon="⚠️")
                else:
                     st.markdown("""
                     <div class="safe-alert">
                        <h5 style="color:#15803d; margin:0;">✅ Routine Approved</h5>
                        <p style="margin:0; font-size:0.9rem;">No conflicts detected. Your routine appears balanced and safe.</p>
                     </div>
                     """, unsafe_allow_html=True)
                     st.toast("Routine looks perfect!", icon="✨")

            st.markdown("---")
            
            # Cek apakah jurnal untuk tanggal ini sudah ada
            journal_df = st.session_state["journal_data"]
            c_date_str = c_date.strftime("%Y-%m-%d")
            
            # Pastikan kolom Date berupa string untuk perbandingan
            if not journal_df.empty and "Date" in journal_df.columns:
                journal_df["Date"] = journal_df["Date"].astype(str)
            
            entry_exists = False
            if not journal_df.empty:
                entry_exists = (journal_df["Date"] == c_date_str).any()

            # Reset konfirmasi jika tanggal berubah
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
                if conflicts_am or conflicts_pm:
                    status_str = "⚠️ Conflict Detected"
                elif final_warn_am or final_warn_pm or cross_warn:
                    status_str = "ℹ️ Warnings"
                
                new_row = {
                    "Date": c_date_str,
                    "Day Products": ", ".join(selected_am),
                    "Night Products": ", ".join(selected_pm),
                    "Status": status_str
                }
                
                if entry_exists:
                    # Update row yang ada
                    idx = journal_df[journal_df["Date"] == c_date_str].index
                    for i in idx:
                        journal_df.at[i, "Day Products"] = new_row["Day Products"]
                        journal_df.at[i, "Night Products"] = new_row["Night Products"]
                        journal_df.at[i, "Status"] = new_row["Status"]
                    st.session_state["journal_data"] = journal_df
                    success_msg = "Journal Updated!"
                else:
                    # Tambah row baru
                    new_entry = pd.DataFrame([new_row])
                    st.session_state["journal_data"] = pd.concat([
                        journal_df, new_entry
                    ], ignore_index=True)
                    success_msg = "Journal Entry Saved!"
                
                # Save to Google Sheets (if configured)
                # Kita kirim full dataframe agar sinkron (overwrite)
                gs_success, gs_msg = sync_journal_to_gsheets(st.session_state["journal_data"])
                
                # Always save to local CSV as backup
                st.session_state["journal_data"].to_csv("journal_history.csv", index=False)
                
                if gs_success:
                    st.toast(gs_msg, icon="☁️")
                else:
                    st.toast("Saved to local storage (Offline)", icon="💾")
                
                st.success(success_msg)
                time.sleep(1)
                st.rerun()

            # --- BREAKOUT ANALYSIS FEATURE ---
            st.markdown("---")
            st.markdown("### 🚨 Breakout Detector")
            st.caption("Analisis potensi penyebab breakout berdasarkan riwayat pemakaian produk 2 minggu terakhir.")

            is_breakout = st.checkbox("Apakah anda mengalami breakout / jerawat meradang hari ini?")

            if is_breakout:
                if st.button("🔍 Analisis Breakout (Cek Riwayat 2 Minggu)"):
                    # 1. Ambil data jurnal 14 hari terakhir
                    j_df = st.session_state["journal_data"].copy()
                    if not j_df.empty:
                        # Pastikan format tanggal datetime
                        j_df["Date"] = pd.to_datetime(j_df["Date"], errors='coerce')
                        
                        end_date = pd.Timestamp(date.today())
                        start_date = end_date - timedelta(days=14)
                        
                        mask = (j_df["Date"] >= start_date) & (j_df["Date"] <= end_date)
                        recent_logs = j_df.loc[mask]
                        
                        if recent_logs.empty:
                            st.warning("Tidak ada data jurnal dalam 14 hari terakhir.")
                        else:
                            st.info(f"Menganalisis {len(recent_logs)} entri jurnal dari {start_date.date()} sampai {end_date.date()}...")
                            
                            # Analisis Status Jurnal (Warnings)
                            warn_mask = recent_logs["Status"].astype(str).str.contains("Warning|Conflict", case=False)
                            warn_logs = recent_logs[warn_mask]
                            
                            if not warn_logs.empty:
                                st.warning(f"⚠️ Terdeteksi {len(warn_logs)} hari dengan peringatan konflik/risiko dalam 2 minggu terakhir:")
                                for _, w_row in warn_logs.iterrows():
                                    w_date = w_row["Date"].strftime("%Y-%m-%d") if isinstance(w_row["Date"], pd.Timestamp) else str(w_row["Date"])
                                    w_status = w_row["Status"]
                                    d_p = str(w_row.get('Day Products', '')).replace('nan', '').strip()
                                    n_p = str(w_row.get('Night Products', '')).replace('nan', '').strip()
                                    w_prods = ", ".join(filter(None, [d_p, n_p]))
                                    st.markdown(f"- **{w_date}**: {w_status} (Produk: {w_prods})")
                                    
                                    # --- RE-ANALYSIS FOR EXPLANATION ---
                                    # Re-construct lists
                                    d_p_list = [x.strip() for x in str(w_row.get('Day Products', '')).split(",") if x.strip()]
                                    n_p_list = [x.strip() for x in str(w_row.get('Night Products', '')).split(",") if x.strip()]
                                    all_p_list = list(set(d_p_list + n_p_list))
                                    
                                    # 1. Check Product Conflicts (using current rules)
                                    c_conf, c_warn = detect_conflicts(all_p_list, df_ing)
                                    
                                    # 2. Check Sunscreen (Heuristic for historical data)
                                    has_spf = any(x in " ".join(d_p_list).lower() for x in ['sunscreen', 'spf', 'sunblock', 'uv'])
                                    weather_notes = []
                                    if d_p_list and not has_spf:
                                        weather_notes.append("⚠️ **Missing Sunscreen**: Wajib jika UV Index >= 3 (Cek riwayat cuaca).")
                                        
                                    # Combine explanations
                                    explanation = c_conf + c_warn + weather_notes
                                    
                                    if explanation:
                                        with st.expander("ℹ️ Penjelasan Potensi Warning"):
                                            for exp in explanation:
                                                # Clean up the string for display
                                                clean_exp = exp.replace("ℹ️ ", "").replace("⚠️ ", "")
                                                st.caption(f"• {clean_exp}")
                                    else:
                                        with st.expander("ℹ️ Penjelasan Potensi Warning"):
                                            st.caption("Warning mungkin disebabkan oleh kondisi cuaca spesifik (Kelembapan Rendah/UV Tinggi) pada tanggal tersebut yang tidak dapat direkonstruksi saat ini.")
                            
                            # 2. Kumpulkan semua produk unik yang dipakai
                            used_products = set()
                            for _, r in recent_logs.iterrows():
                                d_p = [x.strip() for x in str(r.get("Day Products", "")).split(",") if x.strip()]
                                n_p = [x.strip() for x in str(r.get("Night Products", "")).split(",") if x.strip()]
                                used_products.update(d_p)
                                used_products.update(n_p)
                            
                            if not used_products:
                                st.warning("Tidak ada produk yang tercatat dalam periode ini.")
                            else:
                                # 3. Cek Ingredients (Acne & Irritant)
                                st.markdown(f"**Produk yang dipakai ({len(used_products)}):**")
                                st.caption(", ".join(list(used_products)))
                                
                                if "detailed_analysis" in df_ing.columns:
                                    # Initialize the suspect lists before the loop
                                    suspects_acne = []
                                    suspects_irr = []
                                    
                                    # Filter df_ing untuk produk yang dipakai saja
                                    subset_ing = df_ing[df_ing["nama_produk"].isin(used_products)]
                                    
                                    if subset_ing.empty:
                                        st.warning("⚠️ Data ingredients belum tersedia untuk produk-produk ini. Pastikan sudah menjalankan Sync Data Pipeline.")
                                    
                                    # Cek apakah ada produk yang datanya kosong ("[]")
                                    empty_data_prods = subset_ing[subset_ing["detailed_analysis"] == "[]"]["nama_produk"].tolist()
                                    if empty_data_prods:
                                        st.caption(f"ℹ️ Produk berikut sudah di-scan tapi tidak ditemukan data ingredients detail: {', '.join(empty_data_prods)}")

                                    debug_info = []
                                    
                                    for _, row in subset_ing.iterrows():
                                        try:
                                            raw_json = row.get("detailed_analysis")
                                            
                                            # Enhanced validation for raw_json
                                            if not raw_json or raw_json == "[]" or raw_json.strip() == "":
                                                debug_info.append(f"No data for {row['nama_produk']}")
                                                continue
                                                
                                            try:
                                                dets = json.loads(raw_json)
                                            except json.JSONDecodeError as e:
                                                debug_info.append(f"JSON error for {row['nama_produk']}: {str(e)}")
                                                continue
                                                
                                            if not isinstance(dets, list):
                                                debug_info.append(f"Invalid data format for {row['nama_produk']}")
                                                continue
                                                
                                            for d in dets:
                                                # Ensure d is a dictionary
                                                if not isinstance(d, dict):
                                                    continue
                                                    
                                                # Get scores with proper validation
                                                try:
                                                    # Try Capitalized keys (CosDNA standard) first, then lowercase
                                                    ac_raw = d.get("Acne") if d.get("Acne") is not None else d.get("acne", 0)
                                                    ir_raw = d.get("Irritant") if d.get("Irritant") is not None else d.get("irritant", 0)
                                                    
                                                    ac_val = int(float(ac_raw)) if ac_raw is not None else 0
                                                    ir_val = int(float(ir_raw)) if ir_raw is not None else 0
                                                except (ValueError, TypeError):
                                                    ac_val = 0
                                                    ir_val = 0
                                                    
                                                # Get ingredient name with validation
                                                ingredient_name = d.get("Ingredient") or d.get("name") or "Unknown"
                                                if not ingredient_name or ingredient_name.strip() == "":
                                                    continue
                                                    
                                                if ac_val >= 3:
                                                    suspects_acne.append({
                                                        "product": row["nama_produk"],
                                                        "ingredient": ingredient_name,
                                                        "score": ac_val
                                                    })
                                                
                                                if ir_val >= 3:
                                                    suspects_irr.append({
                                                        "product": row["nama_produk"],
                                                        "ingredient": ingredient_name,
                                                        "score": ir_val
                                                    })
                                                    
                                        except Exception as e:
                                            debug_info.append(f"Error processing {row['nama_produk']}: {str(e)}")
                                            continue
                                    
                                    # Show debug info if no results found
                                    if not suspects_acne and not suspects_irr and debug_info:
                                        with st.expander("🔍 Debug Information"):
                                            for info in debug_info[:10]:  # Show first 10 debug messages
                                                st.caption(info)
                                    
                                    # Tampilkan Hasil
                                    c_res1, c_res2 = st.columns(2)
                                    
                                    with c_res1:
                                        st.markdown("#### 🌋 Acne Triggers skor (1-5)")
                                        if suspects_acne:
                                            suspects_acne.sort(key=lambda x: x["score"], reverse=True)
                                            for s in suspects_acne:
                                                color = "#b91c1c" if s["score"] >= 3 else "#d97706"
                                                st.markdown(f"- <span style='color:{color}; font-weight:bold;'>{s['ingredient']} ({s['score']})</span> <span style='font-size:0.8em; color:#64748b;'>in {s['product']}</span>", unsafe_allow_html=True)
                                        else:
                                            st.success("Tidak ditemukan ingredients dengan skor Acne tinggi (>= 3).")
                                            
                                    with c_res2:
                                        st.markdown("#### 🔥 Irritant Triggers skor (1-5)")
                                        if suspects_irr:
                                            suspects_irr.sort(key=lambda x: x["score"], reverse=True)
                                            for s in suspects_irr:
                                                color = "#b91c1c" if s["score"] >= 3 else "#d97706"
                                                st.markdown(f"- <span style='color:{color}; font-weight:bold;'>{s['ingredient']} ({s['score']})</span> <span style='font-size:0.8em; color:#64748b;'>in {s['product']}</span>", unsafe_allow_html=True)
                                        else:
                                            st.success("Tidak ditemukan ingredients dengan skor Irritant tinggi (>= 3).")
                                else:
                                    st.error("Data detail ingredients belum tersedia. Silakan jalankan Sync Data Pipeline.")
                    else:
                        st.warning("Data jurnal kosong.")

    with tab2:
        st.markdown("### 📊 Personal Skin Tracker History")
        st.caption("History of your logged routines.")
        
        if not st.session_state["journal_data"].empty:
            st.dataframe(st.session_state["journal_data"], width="stretch")
            
            st.markdown("---")

            with st.expander("🗑️ Delete Specific Entry"):
                dates_list = st.session_state["journal_data"]["Date"].astype(str).unique().tolist()
                dates_list.sort(reverse=True)
                sel_del_date = st.selectbox("Select Date to Remove:", dates_list, key="del_date_sel")
                
                if st.button("Delete Selected Entry"):
                    st.session_state["journal_data"] = st.session_state["journal_data"][st.session_state["journal_data"]["Date"].astype(str) != sel_del_date]
                    st.session_state["journal_data"].to_csv("journal_history.csv", index=False)
                    sync_journal_to_gsheets(st.session_state["journal_data"])
                    st.success(f"Deleted entry for {sel_del_date}")
                    time.sleep(0.5)
                    st.rerun()

            if st.button("🗑️ Clear All History"):
                st.session_state["journal_data"] = pd.DataFrame(columns=["Date", "Day Products", "Night Products", "Status"])
                st.session_state["journal_data"].to_csv("journal_history.csv", index=False)
                sync_journal_to_gsheets(st.session_state["journal_data"])
                st.rerun()
                
            # Export button
            csv_data = st.session_state["journal_data"].to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📤 Export to CSV",
                data=csv_data,
                file_name=f"skincare_journal_{today}.csv",
                mime="text/csv"
            )
        else:
            st.info("No journal entries yet. Start logging in the 'Routine Conflict Checker' tab.")

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
            
            # Calculate PAO Expiry (approx 30 days/month)
            df_disp["pao_days"] = df_disp["pao_bulan"].fillna(12) * 30
            pao_expiry_calc = df_disp["open_date"] + pd.to_timedelta(df_disp["pao_days"], unit='D')
            
            # PAO date cannot exceed the expiry date. The effective expiry is the earlier of the two.
            df_disp["pao_expiry"] = pd.concat([pao_expiry_calc, df_disp["expiry_date"]], axis=1).min(axis=1)
            df_disp["pao_expiry_display"] = df_disp["pao_expiry"].dt.date
            
            def get_status(row):
                now = row["today"]
                exp = row["expiry_date"]
                pao = row["pao_expiry"]
                
                if pd.notnull(exp) and now >= exp:
                    return "❌ Expired"
                if pd.notnull(pao) and now >= pao:
                    return "❌ PAO Exceeded"
                
                if pd.notnull(exp) and 0 <= (exp - now).days <= 30:
                    return "⚠️ Expiring Soon"
                if pd.notnull(pao) and 0 <= (pao - now).days <= 30:
                    return "⚠️ PAO Ending Soon"
                    
                return "✅ Good"
            
            df_disp["Status"] = df_disp.apply(get_status, axis=1)
            
            if "catatan" not in df_disp.columns:
                df_disp["catatan"] = ""

            st.dataframe(
                df_disp,
                column_config={
                    "nama_produk": "Product",
                    "kategori": "Category",
                    "pao_bulan": st.column_config.NumberColumn("PAO (Mo)"),
                    "tanggal_kadaluwarsa": st.column_config.DateColumn("Expiry Date"),
                    "pao_expiry_display": st.column_config.DateColumn("PAO Date"),
                    "catatan": "Ingredients",
                    "Status": "Condition",
                },
                column_order=["nama_produk", "kategori", "pao_bulan", "tanggal_kadaluwarsa", "pao_expiry_display", "Status", "catatan"],
                width="stretch",
                height=500
            )
            
            with st.expander("🗑️ Remove Product"):
                to_del = st.selectbox("Select product to remove:", df_inv_sql["id_produk"].astype(str) + " - " + df_inv_sql["nama_produk"])
                if st.button("Delete Permanently"):
                    pid = int(to_del.split(" - ")[0])
                    delete_inventory(engine, pid)
                    st.success("Product removed.")
                    st.rerun()

    with tab_add:
        st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
        
        # --- FITUR BARU: Search CosDNA ---
        st.markdown("#### 🔍 Search & Add")
        col_s1, col_s2 = st.columns([3, 1])
        search_kw = col_s1.text_input("Search Product Name", key="search_cosdna_input")
        
        if col_s2.button("Search", key="btn_search_cosdna"):
            if search_kw:
                with st.spinner("Searching..."):
                    results = search_cosdna(search_kw)
                    st.session_state["cosdna_results"] = results
                    if not results:
                        st.warning("No results found.")
        
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
                                  tanggal_buka=open_dt, pao_bulan=pao, tanggal_kadaluwarsa=exp_dt,
                                  catatan=note)
                    st.success("Product Added Successfully")
                    st.session_state.pop("form_prod", None)
                    st.session_state.pop("form_notes", None)
                    st.session_state.pop("cosdna_results", None)
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
        st.markdown("</div>", unsafe_allow_html=True)

elif nav == "Ingredient Scanner":
    st.markdown("### 🔎 Product Composition Analysis")
    st.caption("Powered by Web Scraping & Heuristic Analysis")

    st.markdown("#### Search & Analyze")
    col_scan1, col_scan2 = st.columns([3, 1])
    scan_kw = col_scan1.text_input("Enter Product Name:", key="scan_cosdna_input")
    
    if col_scan2.button("Search", key="btn_scan_cosdna"):
        if scan_kw:
            with st.spinner("Searching..."):
                results = search_cosdna(scan_kw)
                st.session_state["scan_results"] = results
                if not results:
                    st.warning("No results found.")

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
        
        # Summary Metrics
        df_det = pd.DataFrame(details)
        if not df_det.empty:
            # Convert numeric columns safely
            df_det['Acne'] = pd.to_numeric(df_det['Acne'], errors='coerce').fillna(0)
            df_det['Irritant'] = pd.to_numeric(df_det['Irritant'], errors='coerce').fillna(0)
            
            high_acne = df_det[df_det['Acne'] >= 3]
            high_irritant = df_det[df_det['Irritant'] >= 3]
            
            m1, m2, m3 = st.columns(3)
            m1.metric("Total Ingredients", len(df_det))
            m2.metric("Acne Triggers", len(high_acne), delta_color="inverse" if len(high_acne)>0 else "normal")
            m3.metric("Irritant Triggers", len(high_irritant), delta_color="inverse" if len(high_irritant)>0 else "normal")
            
            st.markdown("#### 📋 Detailed Ingredient Breakdown")
            st.dataframe(
                df_det, 
                column_config={
                    "Ingredient": "Ingredient Name",
                    "Function": "Function/Purpose",
                    "Acne": st.column_config.NumberColumn("Acne Rating (0-5)", help="Higher is worse"),
                    "Irritant": st.column_config.NumberColumn("Irritant Rating (0-5)", help="Higher is worse")
                },
                width="stretch",
                hide_index=True
            )
            
            if not high_acne.empty:
                st.warning(f"⚠️ **Acne Alert:** Contains {', '.join(high_acne['Ingredient'].tolist())}")
            if not high_irritant.empty:
                st.error(f"🔥 **Irritant Alert:** Contains {', '.join(high_irritant['Ingredient'].tolist())}")
            
            st.markdown("#### 🧠 Analysis Conclusion")
            if not high_acne.empty or not high_irritant.empty:
                 st.markdown("""
                <div class="safety-alert">
                    <h5 style="color:#b91c1c; margin:0;">⚠️ Caution Recommended</h5>
                    <p style="margin:0; font-size:0.9rem;">This product contains high-risk ingredients for acne or irritation. Not recommended for sensitive skin without patch testing.</p>
                </div>
                """, unsafe_allow_html=True)
            elif (df_det['Acne'] > 0).any() or (df_det['Irritant'] > 0).any():
                 st.markdown("""
                <div class="warning-alert">
                    <h5 style="color:#a16207; margin:0;">✨ Generally Safe</h5>
                    <p style="margin:0; font-size:0.9rem;">Contains some ingredients with low-level risks. Generally safe for most users.</p>
                </div>
                """, unsafe_allow_html=True)
            else:
                 st.markdown("""
                <div class="safe-alert">
                    <h5 style="color:#15803d; margin:0;">✅ Excellent Safety Profile</h5>
                    <p style="margin:0; font-size:0.9rem;">No significant acne or irritation triggers detected. Suitable for sensitive skin.</p>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No detailed ingredient data found for this product.")

elif nav == "Data Export":
    st.markdown("### 📤 Data Export Center")
    st.caption("Download your data for academic reporting or backup.")
    
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    
    c1, c2 = st.columns(2)
    
    def to_csv(df): return df.to_csv(index=False).encode('utf-8')
    
    with c1:
        st.markdown("**Daily Context (Gold)**")
        if not df_ctx.empty:
            st.download_button("Download CSV", to_csv(df_ctx), "gold_context.csv", "text/csv", key="btn_ctx")
        else:
            st.button("No Data", disabled=True)
            
    with c2:
        st.markdown("**Inventory Backup (SQL)**")
        if not df_inv_sql.empty:
            st.download_button("Download CSV", to_csv(df_inv_sql), "inventory.csv", "text/csv", key="btn_inv")
        else:
            st.button("No Data", disabled=True)
            
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("""
<div style="text-align:center; color:#cbd5e1; padding: 20px; font-size:0.8rem;">
    Skincare Tracker • Intelligent Data Pipeline • 2025
</div>
""", unsafe_allow_html=True)