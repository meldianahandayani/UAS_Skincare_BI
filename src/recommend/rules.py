import pandas as pd

def make_recommendation(uvi_am, hum_am, hum_pm, kondisi_kulit, reaksi_kulit, has_sunscreen: bool, conflict_notes: str):
    am, pm, warn = [], [], []

    kondisi = (kondisi_kulit or "").lower()
    reaksi = (reaksi_kulit or "").lower()

    # UV (AM) → aksi sunscreen
    if uvi_am is not None:
        try:
            u = float(uvi_am)
        except:
            u = None
        if u is not None:
            if u >= 8:
                am.append(f"UV Pagi/Siang sangat tinggi ({u:.1f}) → sunscreen wajib + reapply lebih sering.")
            elif u >= 3:
                am.append(f"UV Pagi/Siang sedang ({u:.1f}) → sunscreen wajib.")
            else:
                am.append(f"UV Pagi/Siang rendah ({u:.1f}) → sunscreen tetap disarankan.")

            if u >= 3 and not has_sunscreen:
                warn.append("Stok sunscreen tidak ditemukan di inventory → pertimbangkan beli/siapkan sunscreen.")

    # Humidity AM
    if hum_am is not None:
        try:
            h = float(hum_am)
        except:
            h = None
        if h is not None:
            if h <= 45 or "kering" in kondisi:
                am.append("Kelembapan Pagi rendah → moisturizer lebih rich.")
            else:
                am.append("Kelembapan Pagi cukup → moisturizer gel/light cukup.")

    # Humidity PM (Night)
    if hum_pm is not None:
        try: h_pm = float(hum_pm)
        except: h_pm = None
        if h_pm is not None:
             if h_pm <= 50:
                 pm.append("Udara malam kering → pertimbangkan sleeping mask/occlusive.")

    # Reaksi kulit → recovery
    if "kemerahan" in reaksi or "irit" in reaksi:
        pm.append("Recovery night: fokus soothing + hydrating, tunda active kuat.")
        warn.append("Kulit sedang reaktif → hindari exfoliant/retinoid dulu.")
    else:
        pm.append("Ikuti rutinitas malam sesuai rencana (jika ada).")

    if conflict_notes:
        warn.append(f"Catatan ingredients: {conflict_notes}")

    return " | ".join(am), " | ".join(pm), " | ".join(warn)

def detect_conflicts_enhanced(product_names: list[str], ingredients_df=None) -> tuple[list[str], list[str]]:
    """
    Enhanced conflict detection based on product names and ingredients
    Returns: (conflicts, warnings)
    """
    conflicts = []
    warnings = []
    
    # Combine product names for analysis
    combined_text = " ".join(product_names).lower()
    
    # Ingredient keywords for conflict detection
    retinol_keywords = ["retinol", "retinyl", "retinal", "granactive retinoid", "adapalene", "tretinoin"]
    vit_c_keywords = ["vitamin c", "ascorbic", "ethyl ascorbic", "magnesium ascorbyl"]
    exfoliant_keywords = [
        "aha", "bha", "pha", 
        "glycolic", "salicylic", "lactic", "mandelic", "citric acid",
        "refining", "peeling", "exfoliating", "clarifying", "acid"
    ]
    benzoyl_keywords = ["benzoyl peroxide", "benzolac"]
    niacinamide_keywords = ["niacinamide", "nicotinamide"]
    
    # Check for active ingredients
    has_retinol = any(kw in combined_text for kw in retinol_keywords)
    has_vit_c = any(kw in combined_text for kw in vit_c_keywords)
    has_exfoliant = any(kw in combined_text for kw in exfoliant_keywords)
    has_benzoyl = any(kw in combined_text for kw in benzoyl_keywords)
    has_niacinamide = any(kw in combined_text for kw in niacinamide_keywords)
    
    # Critical conflicts (high risk)
    if has_retinol and has_exfoliant:
        conflicts.append("❌ **BAHAYA: Retinol + AHA/BHA/Exfoliant**. Risiko iritasi tinggi dan kerusakan skin barrier.")
    
    if has_retinol and has_benzoyl:
        conflicts.append("❌ **BAHAYA: Retinol + Benzoyl Peroxide**. Bahan aktif dapat saling menonaktifkan.")
    
    if has_retinol and has_vit_c:
        conflicts.append("⛔ **DANGER: Retinol + Vitamin C**. Risiko iritasi tinggi. Gunakan di waktu berbeda.")
    
    # Warnings (moderate risk)
    if has_exfoliant and has_vit_c:
        warnings.append("⚠️ **PERINGATAN: AHA/BHA + Vitamin C**. Risiko kemerahan. Gunakan di waktu berbeda.")
    
    if has_benzoyl and has_vit_c:
        warnings.append("⚠️ **PERINGATAN: Benzoyl Peroxide + Vitamin C**. Potensi degradasi Vitamin C.")
    
    # Additional analysis from ingredients if available
    if ingredients_df is not None and not ingredients_df.empty:
        # Filter to only selected products to avoid spamming warnings for the whole database
        relevant_ing = ingredients_df[ingredients_df['nama_produk'].isin(product_names)]
        
        # Analyze ingredients for comedogenic and irritant risks
        for _, row in relevant_ing.iterrows():
            if "ingredients_list" in row and pd.notna(row["ingredients_list"]):
                ing_text = str(row["ingredients_list"]).lower()
                
                # Check for high-risk ingredients
                high_risk = ["alcohol denat", "fragrance", "parfum", "menthol"]
                comedogenic = ["coconut oil", "isopropyl myristate", "laureth-4"]
                
                if any(risk in ing_text for risk in high_risk):
                    warnings.append(f"⚠️ Produk '{row.get('nama_produk', 'Unknown')}' mengandung bahan iritan tinggi.")
                
                if any(come in ing_text for come in comedogenic):
                    warnings.append(f"⚠️ Produk '{row.get('nama_produk', 'Unknown')}' berisiko menyumbat pori.")
    
    # Safety recommendations
    if not conflicts and not warnings:
        warnings.append("✅ **AMAN**: Kombinasi produk terlihat aman berdasarkan analisis ingredient.")
    
    return conflicts, warnings

def analyze_ingredient_safety(ingredients: list[str]) -> dict:
    """
    Analyze ingredient safety and provide recommendations
    """
    analysis = {
        "comedogenic_risk": [],
        "irritant_risk": [],
        "safe_ingredients": [],
        "recommendations": []
    }
    
    comedogenic_ingredients = {
        "coconut oil": 4,
        "isopropyl myristate": 5,
        "laureth-4": 4,
        "cocoa butter": 4,
        "algae extract": 3,
        "seaweed extract": 2,
        "caramel": 1
    }
    
    irritant_ingredients = {
        "alcohol denat": "High",
        "fragrance": "Moderate",
        "parfum": "Moderate", 
        "menthol": "High",
        "sls": "High",
        "sodium lauryl sulfate": "High",
        "camphor": "Moderate"
    }
    
    beneficial_ingredients = {
        "hyaluronic acid": "Hydration",
        "niacinamide": "Oil control & brightening",
        "ceramides": "Barrier repair",
        "peptides": "Anti-aging",
        "glycerin": "Moisturizing",
        "aloe vera": "Soothing"
    }
    
    ing_text = " ".join(ingredients).lower()
    
    # Check comedogenic risk
    for ing, risk in comedogenic_ingredients.items():
        if ing in ing_text:
            analysis["comedogenic_risk"].append(f"{ing.title()} (Risk Level: {risk}/5)")
    
    # Check irritant risk
    for ing, risk in irritant_ingredients.items():
        if ing in ing_text:
            analysis["irritant_risk"].append(f"{ing.title()} ({risk} Risk)")
    
    # Check beneficial ingredients
    for ing, benefit in beneficial_ingredients.items():
        if ing in ing_text:
            analysis["safe_ingredients"].append(f"{ing.title()} - {benefit}")
    
    # Generate recommendations
    if analysis["comedogenic_risk"]:
        analysis["recommendations"].append("🚨 **Comedogenic Alert**: Produk berisiko menyumbat pori. Monitor untuk breakout.")
    
    if analysis["irritant_risk"]:
        analysis["recommendations"].append("⚠️ **Irritant Alert**: Produk mengandung bahan刺激性. Patch test disarankan.")
    
    if analysis["safe_ingredients"]:
        analysis["recommendations"].append("✅ **Beneficial**: Produk mengandung bahan baik untuk kulit.")
    
    if not analysis["comedogenic_risk"] and not analysis["irritant_risk"]:
        analysis["recommendations"].append("✅ **Low Risk**: Produk cenderung aman untuk sebagian besar jenis kulit.")
    
    return analysis

def analyze_daily_safety(am_products: list[str], pm_products: list[str], 
                        uvi_am: float, hum_am: float, hum_pm: float, 
                        ingredients_df=None, am_has_sunscreen: bool = False) -> list[str]:
    """
    Analyze the safety of the combined AM and PM routine considering weather.
    """
    warnings = []
    
    # Helper to get combined text (product names + ingredients)
    def get_content(prod_list):
        text = " ".join(prod_list).lower()
        if ingredients_df is not None and not ingredients_df.empty:
            rel = ingredients_df[ingredients_df['nama_produk'].isin(prod_list)]
            if not rel.empty and 'ingredients_list' in rel.columns:
                ing_text = " ".join(rel['ingredients_list'].fillna("").astype(str).tolist()).lower()
                text += " " + ing_text
        return text

    am_content = get_content(am_products)
    pm_content = get_content(pm_products)
    
    # Keywords
    retinol = ["retinol", "retinyl", "tretinoin", "adapalene"]
    exfoliants = ["aha", "bha", "glycolic", "salicylic", "lactic", "acid"]
    
    has_retinol_am = any(k in am_content for k in retinol)
    has_exfoliant_am = any(k in am_content for k in exfoliants)
    has_retinol_pm = any(k in pm_content for k in retinol)
    has_exfoliant_pm = any(k in pm_content for k in exfoliants)
    
    # 1. Weather Checks (AM Focus)
    if uvi_am is not None and float(uvi_am) >= 3:
        if not am_has_sunscreen and am_products:
             warnings.append(f"☀️ **Missing Sunscreen**: Average UV Index is {uvi_am:.1f} (High). Sunscreen is mandatory for Day Routine!")
        
        if has_retinol_am:
            warnings.append("☀️ **High UV Warning**: Retinol in Day routine increases sun sensitivity. Ensure strong SPF!")
        if has_exfoliant_am:
            warnings.append("☀️ **High UV Warning**: Exfoliants (AHA/BHA) in Day routine increase sun sensitivity. Ensure strong SPF!")
            
    if hum_am is not None and float(hum_am) < 50:
        if has_exfoliant_am:
            warnings.append(f"💧 **Low Day Humidity ({hum_am:.0f}%)**: Exfoliating in dry weather may cause extra dryness.")
            
    if hum_pm is not None and float(hum_pm) < 50:
        if has_exfoliant_pm:
            warnings.append(f"💧 **Low Night Humidity ({hum_pm:.0f}%)**: Exfoliating in dry night air may cause dryness.")

    # 2. Daily Load Conflicts
    if (has_retinol_am or has_retinol_pm) and (has_exfoliant_am or has_exfoliant_pm):
         warnings.append("⚠️ **Over-Exfoliation Risk**: Using Retinol and Exfoliants on the same day can damage skin barrier.")
         
    if has_retinol_am and has_retinol_pm:
         warnings.append("⚠️ **High Retinol Load**: Using Retinol twice a day is usually too harsh.")

    return warnings
