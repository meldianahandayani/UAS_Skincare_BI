import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import date, datetime, timedelta
from pathlib import Path
import io
import zipfile
import os

# Import fungsi dari pipeline
from src.pipeline import run_all
from src.utils.config import DB_URL

# =========================================================
# 1. KONFIGURASI HALAMAN & CSS
# =========================================================
st.set_page_config(
    page_title="Skincare Tracker",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Daftar Kota untuk Pilihan Lokasi
CITIES = {
    "Jakarta": {"lat": -6.2088, "lon": 106.8456},
    "Banjarmasin": {"lat": -3.3194, "lon": 114.5908},
    "Bandung": {"lat": -6.9175, "lon": 107.6191},
    "Surabaya": {"lat": -7.2575, "lon": 112.7521},
    "Yogyakarta": {"lat": -7.7955, "lon": 110.3695},
    "Medan": {"lat": 3.5952, "lon": 98.6722},
    "Makassar": {"lat": -5.1477, "lon": 119.4328},
    "Denpasar (Bali)": {"lat": -8.6705, "lon": 115.2126},
}

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
    </style>
    """,
    unsafe_allow_html=True,
)

# =========================================================
# 2. DEFINISI FUNGSI (Harus sebelum dipanggil)
# =========================================================
def get_engine():
    if not DB_URL: return None
    try: return create_engine(DB_URL)
    except: return None

def read_inventory(engine) -> pd.DataFrame:
    try:
        return pd.read_sql("SELECT * FROM inventory_skincare ORDER BY nama_brand, nama_produk;", engine)
    except:
        return pd.DataFrame()

def add_inventory(engine, **kwargs):
    q = text("""
        INSERT INTO inventory_skincare 
        (nama_brand, nama_produk, kategori, tanggal_beli, tanggal_buka, pao_bulan, tanggal_kedaluwarsa, volume_ml, harga_idr, catatan)
        VALUES (:nama_brand, :nama_produk, :kategori, :tanggal_beli, :tanggal_buka, :pao_bulan, :tanggal_kedaluwarsa, :volume_ml, :harga_idr, :catatan)
    """)
    with engine.begin() as conn: conn.execute(q, kwargs)

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

def detect_conflicts(selected: list[str], ingredients_df: pd.DataFrame):
    conflicts = []
    scrape_notes = []
    
    combined_names = " ".join(selected).lower()
    combined_ingredients = ""
    
    if not ingredients_df.empty and "nama_produk" in ingredients_df.columns:
        sub = ingredients_df[ingredients_df["nama_produk"].isin(selected)]
        if "ingredients_list" in sub.columns:
            combined_ingredients = " ".join(sub["ingredients_list"].dropna().astype(str).tolist()).lower()
        if "conflict_rules" in sub.columns:
            scrape_notes = [f"ℹ️ {x}" for x in sub["conflict_rules"].dropna().unique() if x]

    full_check_text = combined_names + " " + combined_ingredients

    k_retinol = ["retinol", "retinyl", "retinal", "granactive retinoid", "adapalene", "tretinoin"]
    k_exfo = [
        "aha", "bha", "pha", 
        "glycolic", "salicylic", "lactic", "mandelic", "citric acid",
        "refining", "peeling", "exfoliating", "clarifying", "acid"
    ]
    k_vitc = ["vitamin c", "ascorbic", "ethyl ascorbic", "magnesium ascorbyl"]

    has_retinol = any(x in full_check_text for x in k_retinol)
    has_exfoliant = any(x in full_check_text for x in k_exfo)
    has_vitc = any(x in full_check_text for x in k_vitc)
    has_benzoyl = "benzoyl peroxide" in full_check_text

    if has_retinol and has_exfoliant:
        conflicts.append("❌ **BAHAYA: Retinol + Exfoliant (AHA/BHA/Refining)**. Risiko iritasi tinggi dan kerusakan skin barrier.")
    if has_retinol and has_vitc:
        conflicts.append("⚠️ **PERINGATAN: Retinol + Vitamin C**. Potensi iritasi meningkat. Gunakan di waktu berbeda (Pagi/Malam).")
    if has_retinol and has_benzoyl:
        conflicts.append("❌ **BAHAYA: Retinol + Benzoyl Peroxide**. Bahan aktif dapat saling menonaktifkan.")

    return conflicts, scrape_notes

def analyze_risk(ing_list: list[str]):
    comedogenic = ["coconut oil", "isopropyl myristate", "laureth-4", "cocoa butter", "algae extract"]
    irritants = ["alcohol denat", "fragrance", "parfum", "menthol", "sls", "sodium lauryl sulfate"]
    
    found_c = [x for x in comedogenic if any(x in i.lower() for i in ing_list)]
    found_i = [x for x in irritants if any(x in i.lower() for i in ing_list)]
    
    return found_c, found_i

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
    
    # Dropdown Pilihan Kota
    selected_city_name = st.selectbox("Select City:", list(CITIES.keys()), index=1)
    selected_coords = CITIES[selected_city_name]
    
    st.markdown("---")
    st.markdown("**System Controls**")
    
    if st.button("🔄 Sync Data Pipeline", use_container_width=True):
        with st.spinner(f"Updating weather for {selected_city_name}..."):
            # KIRIM LAT/LON KE PIPELINE
            res = run_all(lat=selected_coords["lat"], lon=selected_coords["lon"])
        
        st.session_state["pipeline_run"] = datetime.now()
        st.session_state["last_city"] = selected_city_name
        st.success(f"Synced for {selected_city_name} ✅")
        st.rerun()
        
    engine = get_engine()
    st.markdown(f"<div style='font-size:0.8rem; color:#94a3b8; margin-top:10px;'>Database: {'🟢 Connected' if engine else '🔴 Disconnected'}</div>", unsafe_allow_html=True)

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

# =========================================================
# 5. KONTEN HALAMAN UTAMA
# =========================================================
if nav == "Dashboard":
    col_l, col_r = st.columns([3, 1])
    with col_l:
        st.markdown(f"### 👋 Hello, User")
        st.markdown(f"Skin environment analysis for **{today.strftime('%A, %d %B %Y')}**")
    with col_r:
        # Ambil nama kota dari session state (agar dinamis setelah sync)
        current_city = st.session_state.get("last_city", selected_city_name)
        st.markdown(f"<div style='text-align:right; font-weight:600; color:#ec4899;'>📍 {current_city}, ID</div>", unsafe_allow_html=True)
    
    st.markdown("---")

    w_temp = df_wth.iloc[0]['temp_c'] if not df_wth.empty else 0
    w_hum = df_wth.iloc[0]['humidity'] if not df_wth.empty else 0
    w_uv = df_wth.iloc[0]['uvi'] if not df_wth.empty else 0
    
    c1, c2, c3, c4 = st.columns(4)
    def card(col, label, val, sub):
        col.markdown(f"""
        <div class="glass-card kpi-container">
            <span class="kpi-label">{label}</span>
            <span class="kpi-value">{val}</span>
            <span class="kpi-sub">{sub}</span>
        </div>
        """, unsafe_allow_html=True)

    card(c1, "UV Index", f"{w_uv:.1f}", "Moderate Risk" if w_uv > 3 else "Low Risk")
    card(c2, "Humidity", f"{w_hum:.0f}%", "Hydration Factor")
    card(c3, "Temperature", f"{w_temp:.1f}°C", "Ambient Heat")
    card(c4, "Skin Log", f"{len(df_trk)} Days", "Data Points")
    
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
                    <h3 style="margin-top:0; color:#be185d;">☀️ Morning (AM)</h3>
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
                    <h3 style="margin-top:0; color:#4f46e5;">🌙 Evening (PM)</h3>
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
        st.caption("Select products you plan to layer today to detect dangerous interactions.")
        
        with st.container():
            if df_inv_sql.empty:
                st.info("Inventory is empty. Please add products in the Inventory menu.")
            else:
                options = df_inv_sql["nama_produk"].tolist()
                selected = st.multiselect("Select products:", options)
                
                if selected:
                    st.markdown("---")
                    conflicts, notes = detect_conflicts(selected, df_ing)
                    
                    if conflicts:
                        st.error("🚨 **CONFLICT DETECTED**")
                        for c in conflicts: st.markdown(c)
                    else:
                        st.success("✅ **SAFE COMBINATION**")
                        st.markdown("No known active ingredient conflicts found based on heuristics.")
                    
                    if notes:
                        st.markdown("**Additional Notes:**")
                        for n in notes: st.caption(n)

    with tab2:
        if df_trk.empty:
            st.info("No tracker data available from Google Sheets.")
        else:
            st.dataframe(df_trk, use_container_width=True)

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
            df_disp["expiry_date"] = pd.to_datetime(df_disp["tanggal_kedaluwarsa"])
            df_disp["today"] = pd.to_datetime(today)
            
            df_disp["days_left"] = (df_disp["expiry_date"] - df_disp["today"]).dt.days
            df_disp["freshness"] = df_disp["days_left"].apply(lambda x: max(0, min(365, x)) / 365 if pd.notnull(x) else 0)
            
            st.dataframe(
                df_disp,
                column_config={
                    "nama_brand": "Brand",
                    "nama_produk": "Product",
                    "kategori": st.column_config.SelectboxColumn("Category", width="small"),
                    "freshness": st.column_config.ProgressColumn(
                        "Freshness (1 Year)", 
                        help="Green is fresh, empty is expired",
                        format="%.2f",
                        min_value=0, max_value=1
                    ),
                    "days_left": st.column_config.NumberColumn("Days Left", format="%d days"),
                    "harga_idr": st.column_config.NumberColumn("Price", format="Rp %d"),
                },
                column_order=["nama_brand", "nama_produk", "kategori", "freshness", "days_left", "harga_idr"],
                use_container_width=True,
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
        with st.form("inventory_form"):
            c1, c2 = st.columns(2)
            brand = c1.text_input("Brand")
            prod = c2.text_input("Product Name")
            cat = st.selectbox("Category", ["Cleanser", "Toner", "Serum", "Moisturizer", "Sunscreen", "Exfoliant", "Mask"])
            
            c3, c4, c5 = st.columns(3)
            buy_dt = c3.date_input("Buy Date")
            open_dt = c4.date_input("Open Date")
            exp_dt = c5.date_input("Expiry Date", value=today + timedelta(days=365))
            
            c6, c7, c8 = st.columns(3)
            pao = c6.number_input("PAO (Months)", 12)
            vol = c7.number_input("Volume (ml)", 0)
            price = c8.number_input("Price (IDR)", 0)
            
            note = st.text_area("Notes")
            
            if st.form_submit_button("Save to Shelf"):
                try:
                    add_inventory(engine, nama_brand=brand, nama_produk=prod, kategori=cat, tanggal_beli=buy_dt,
                                  tanggal_buka=open_dt, pao_bulan=pao, tanggal_kedaluwarsa=exp_dt,
                                  volume_ml=vol, harga_idr=price, catatan=note)
                    st.success("Product Added Successfully")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
        st.markdown("</div>", unsafe_allow_html=True)

elif nav == "Ingredient Scanner":
    st.markdown("### 🔎 Product Composition Analysis")
    st.caption("Powered by Web Scraping & Heuristic Analysis")
    
    if df_ing.empty:
        st.info("No scraped ingredient data found in Silver layer.")
    else:
        df_ing["display"] = df_ing["nama_brand"] + " - " + df_ing["nama_produk"]
        choice = st.selectbox("Search Database:", df_ing["display"].unique())
        
        row = df_ing[df_ing["display"] == choice].iloc[0]
        ingredients_raw = str(row.get("ingredients_list", "")).split("|")
        ingredients_clean = [x.strip() for x in ingredients_raw if x.strip()]
        
        st.markdown("---")
        
        comedones, irritants = analyze_risk(ingredients_clean)
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("""<div class="glass-card">
                        <h5 style="color:#be185d;">🚨 Pore Clogging (Comedogenic)</h5>
                        """, unsafe_allow_html=True)
            if comedones:
                st.markdown(f"<span class='badge badge-red'>High Risk</span>", unsafe_allow_html=True)
                st.write(", ".join([f"**{x.title()}**" for x in comedones]))
            else:
                st.markdown(f"<span class='badge badge-green'>Low Risk</span>", unsafe_allow_html=True)
                st.caption("No common pore-clogging ingredients detected.")
            st.markdown("</div>", unsafe_allow_html=True)
            
        with c2:
            st.markdown("""<div class="glass-card">
                        <h5 style="color:#be185d;">🔥 Irritation Potential</h5>
                        """, unsafe_allow_html=True)
            if irritants:
                st.markdown(f"<span class='badge badge-yellow'>Moderate/High Risk</span>", unsafe_allow_html=True)
                st.write(", ".join([f"**{x.title()}**" for x in irritants]))
            else:
                st.markdown(f"<span class='badge badge-green'>Safe</span>", unsafe_allow_html=True)
                st.caption("Suitable for sensitive skin.")
            st.markdown("</div>", unsafe_allow_html=True)
            
        with st.expander("View Full Ingredient List"):
            st.write(ingredients_clean)

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