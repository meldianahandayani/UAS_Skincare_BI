import pandas as pd
import json

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

def display_acne_triggers(ingredients_df, selected_products: list[str] = None) -> str:
    """
    Display high acne trigger ingredients found in products
    Shows ingredients with acne score >= 3
    """
    if ingredients_df is None or ingredients_df.empty:
        return "❌ No ingredient data available"
    
    # Filter to selected products or all if none specified
    if selected_products:
        relevant_products = ingredients_df[ingredients_df['nama_produk'].isin(selected_products)]
    else:
        relevant_products = ingredients_df.copy()
    
    high_risk_triggers = []
    
    # Process each product
    for _, row in relevant_products.iterrows():
        if "detailed_analysis" not in row or pd.isna(row["detailed_analysis"]):
            continue
            
        try:
            # Parse the JSON detailed analysis
            import json
            details = json.loads(row["detailed_analysis"])
            if not details:
                continue
                
            # Convert to DataFrame for easier analysis
            df_det = pd.DataFrame(details)
            
            # Normalize columns if needed
            if 'acne' in df_det.columns and 'Acne' not in df_det.columns:
                df_det.rename(columns={'acne': 'Acne', 'irritant': 'Irritant', 'name': 'Ingredient'}, inplace=True)
            
            if 'Acne' not in df_det.columns: continue
            
            # Find high acne risk ingredients (score >= 3)
            df_det['Acne'] = pd.to_numeric(df_det['Acne'], errors='coerce').fillna(0)
            high_acne = df_det[df_det['Acne'] >= 3]
            
            for _, ingredient in high_acne.iterrows():
                product_name = row['nama_produk']
                ingredient_name = ingredient['Ingredient']
                acne_score = ingredient['Acne']
                
                high_risk_triggers.append({
                    'product': product_name,
                    'ingredient': ingredient_name,
                    'score': acne_score
                })
                
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            continue
    
    # Generate display
    if not high_risk_triggers:
        return "✅ No high acne trigger ingredients found"
    
    # Format the display
    display = "🌋 Acne Triggers\n"
    
    # Group by product for cleaner display
    products_with_triggers = {}
    for trigger in high_risk_triggers:
        product = trigger['product']
        if product not in products_with_triggers:
            products_with_triggers[product] = []
        products_with_triggers[product].append(trigger)
    
    # Display each product and its triggers
    for product, triggers in products_with_triggers.items():
        display += f"\n🔍 **{product}**\n"
        for trigger in triggers:
            display += f"• {trigger['ingredient']} ({trigger['score']})\n"
    
    return display.strip()

def display_irritant_triggers(ingredients_df, selected_products: list[str] = None) -> str:
    """
    Display high irritant trigger ingredients found in products
    Shows ingredients with irritant score >= 3
    """
    if ingredients_df is None or ingredients_df.empty:
        return "❌ No ingredient data available"
    
    # Filter to selected products or all if none specified
    if selected_products:
        relevant_products = ingredients_df[ingredients_df['nama_produk'].isin(selected_products)]
    else:
        relevant_products = ingredients_df.copy()
    
    high_risk_triggers = []
    
    # Process each product
    for _, row in relevant_products.iterrows():
        if "detailed_analysis" not in row or pd.isna(row["detailed_analysis"]):
            continue
            
        try:
            # Parse the JSON detailed analysis
            import json
            details = json.loads(row["detailed_analysis"])
            if not details:
                continue
                
            # Convert to DataFrame for easier analysis
            df_det = pd.DataFrame(details)
            
            # Normalize columns if needed
            if 'irritant' in df_det.columns and 'Irritant' not in df_det.columns:
                df_det.rename(columns={'acne': 'Acne', 'irritant': 'Irritant', 'name': 'Ingredient'}, inplace=True)

            if 'Irritant' not in df_det.columns: continue

            # Find high irritant risk ingredients (score >= 3)
            df_det['Irritant'] = pd.to_numeric(df_det['Irritant'], errors='coerce').fillna(0)
            high_irr = df_det[df_det['Irritant'] >= 3]
            
            for _, ingredient in high_irr.iterrows():
                product_name = row['nama_produk']
                ingredient_name = ingredient['Ingredient']
                irr_score = ingredient['Irritant']
                
                high_risk_triggers.append({
                    'product': product_name,
                    'ingredient': ingredient_name,
                    'score': irr_score
                })
                
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            continue
    
    # Generate display
    if not high_risk_triggers:
        return "✅ No high irritant trigger ingredients found"
    
    # Format the display
    display = "⚠️ Irritant Triggers\n"
    
    # Group by product for cleaner display
    products_with_triggers = {}
    for trigger in high_risk_triggers:
        product = trigger['product']
        if product not in products_with_triggers:
            products_with_triggers[product] = []
        products_with_triggers[product].append(trigger)
    
    # Display each product and its triggers
    for product, triggers in products_with_triggers.items():
        display += f"\n🔍 **{product}**\n"
        for trigger in triggers:
            display += f"• {trigger['ingredient']} ({trigger['score']})\n"
    
    return display.strip()

def create_ingredient_risk_summary(ingredients_df, selected_products: list[str] = None) -> dict:
    """
    Create a comprehensive risk summary for selected products
    """
    if ingredients_df is None or ingredients_df.empty:
        return {"error": "No ingredient data available"}
    
    # Filter to selected products
    if selected_products:
        relevant_products = ingredients_df[ingredients_df['nama_produk'].isin(selected_products)]
    else:
        relevant_products = ingredients_df.copy()
    
    summary = {
        "acne_triggers": [],
        "irritant_triggers": [],
        "safe_products": [],
        "high_risk_products": []
    }
    
    # Analyze each product
    for _, row in relevant_products.iterrows():
        product_name = row['nama_produk']
        has_high_acne = False
        has_high_irr = False
        
        if "detailed_analysis" not in row or pd.isna(row["detailed_analysis"]):
            continue
            
        try:
            details = json.loads(row["detailed_analysis"])
            if not details:
                continue
                
            df_det = pd.DataFrame(details)
            
            # Check for high-risk ingredients
            high_acne = df_det[df_det['Acne'] >= 3]
            high_irr = df_det[df_det['Irritant'] >= 3]
            
            # Process high acne risks
            for _, ingredient in high_acne.iterrows():
                has_high_acne = True
                summary["acne_triggers"].append({
                    'product': product_name,
                    'ingredient': ingredient['Ingredient'],
                    'score': ingredient['Acne']
                })
            
            # Process high irritant risks
            for _, ingredient in high_irr.iterrows():
                has_high_irr = True
                summary["irritant_triggers"].append({
                    'product': product_name,
                    'ingredient': ingredient['Ingredient'],
                    'score': ingredient['Irritant']
                })
            
            # Categorize product safety
            if has_high_acne or has_high_irr:
                summary["high_risk_products"].append(product_name)
            else:
                summary["safe_products"].append(product_name)
                
        except (json.JSONDecodeError, KeyError, TypeError):
            continue
    
    return summary
