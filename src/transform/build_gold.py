import json
import pandas as pd
from datetime import date
from pathlib import Path
from src.utils.paths import part_dir, ensure_dir

def run(d: date, ingredients_df=None):
    """
    Build Gold layer with business logic and recommendations.
    
    Combines silver layer data to generate actionable insights:
    - Daily context from weather + tracker data
    - Personalized recommendations based on inventory + conditions
    """
    
    # Load data from Silver layer
    silver_paths = {
        "tracker": Path(part_dir("silver", "tracker", d)) / "tracker.parquet",
        "weather": Path(part_dir("silver", "weather", d)) / "weather.parquet", 
        "inventory": Path(part_dir("silver", "inventory", d)) / "inventory.parquet"
    }
    
    # Load tracker data
    df_tracker = pd.DataFrame()
    if silver_paths["tracker"].exists():
        df_tracker = pd.read_parquet(silver_paths["tracker"])
    
    # Load weather data  
    df_weather = pd.DataFrame()
    if silver_paths["weather"].exists():
        df_weather = pd.read_parquet(silver_paths["weather"])
    
    # Load inventory data
    df_inventory = pd.DataFrame()
    if silver_paths["inventory"].exists():
        df_inventory = pd.read_parquet(silver_paths["inventory"])
    
    # Build Daily Context
    daily_context = {}
    
    if not df_weather.empty:
        weather_data = df_weather.iloc[0]
        daily_context.update({
            "date": str(d),
            "temperature": weather_data.get("temp_c", 0),
            "humidity": weather_data.get("humidity", 0),
            "uv_index": weather_data.get("uvi", 0),
            "weather_summary": "Normal conditions"
        })
        
        # Weather-based recommendations
        if weather_data.get("uvi", 0) >= 6:
            daily_context["weather_summary"] = "High UV - sunscreen essential"
        elif weather_data.get("humidity", 0) >= 70:
            daily_context["weather_summary"] = "High humidity - light moisturizer"
        elif weather_data.get("humidity", 0) <= 40:
            daily_context["weather_summary"] = "Low humidity - extra hydration needed"
    
    if not df_tracker.empty:
        today_row = df_tracker[df_tracker['tanggal_input'] == str(d)]
        if not today_row.empty:
            status = today_row.iloc[0]['status_keamanan']
            daily_context["today_status"] = status
            daily_context["day_products"] = today_row.iloc[0]['produk_pagi']
            daily_context["night_products"] = today_row.iloc[0]['produk_malam']
        else:
            daily_context["today_status"] = "No entry for today"
            daily_context["day_products"] = ""
            daily_context["night_products"] = ""
    
    # Build Recommendation
    recommendation = {
        "date": str(d),
        "am_plan": "Cleanser → Toner → Serum → Moisturizer → Sunscreen",
        "pm_plan": "Cleanser → Toner → Treatment → Moisturizer",
        "warnings": ""
    }
    
    # Generate weather-based advice
    if not df_weather.empty:
        weather_data = df_weather.iloc[0]
        uv = weather_data.get("uvi", 0)
        temp = weather_data.get("temp_c", 0)
        
        if uv >= 6:
            recommendation["warnings"] += "High UV detected - strict sunscreen application required. "
        if temp >= 30:
            recommendation["warnings"] += "High temperature - consider lighter textures. "
        if weather_data.get("humidity", 0) >= 70:
            recommendation["warnings"] += "High humidity - avoid heavy occlusives. "
        if weather_data.get("humidity", 0) <= 40:
            recommendation["warnings"] += "Low humidity - extra hydration and barrier support needed. "
    
    # Generate inventory-based recommendations
    if not df_inventory.empty and len(df_inventory) > 0:
        # Basic inventory-based suggestions
        has_sunscreen = any("sunscreen" in str(x).lower() for x in df_inventory.get("kategori", []))
        if not has_sunscreen:
            recommendation["warnings"] += "No sunscreen in inventory - essential for daily protection. "
    
    # Save Daily Context to Gold
    if daily_context:
        ctx_dir = ensure_dir(part_dir("gold", "daily_context", d))
        ctx_path = ctx_dir / "daily_context.parquet"
        pd.DataFrame([daily_context]).to_parquet(ctx_path, index=False)
    else:
        ctx_path = "Not Found"
    
    # Save Recommendation to Gold  
    if recommendation:
        rec_dir = ensure_dir(part_dir("gold", "recommendation", d))
        rec_path = rec_dir / "recommendation.parquet"
        pd.DataFrame([recommendation]).to_parquet(rec_path, index=False)
    else:
        rec_path = "Not Found"
    
    return {
        "daily_context": str(ctx_path),
        "recommendation": str(rec_path)
    }
