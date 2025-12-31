import json
import pandas as pd
import os
import s3fs
from datetime import date

def run(d: date, ingredients_df=None):
    """
    Build Gold layer with business logic and recommendations.
    
    Combines silver layer data to generate actionable insights:
    - Daily context from weather + tracker data
    - Personalized recommendations based on inventory + conditions
    """
    # MinIO Setup
    is_docker = os.path.exists("/.dockerenv")
    default_host = "minio" if is_docker else "localhost"
    minio_endpoint = os.getenv("MINIO_ENDPOINT", f"http://{default_host}:9000")
    
    storage_options = {
        "key": os.getenv("MINIO_ACCESS_KEY", "skincare_admin"),
        "secret": os.getenv("MINIO_SECRET_KEY", "skincare_password"),
        "client_kwargs": {"endpoint_url": minio_endpoint}
    }
    
    fs = s3fs.S3FileSystem(**storage_options)
    bucket = "datalake"
    
    # Load data from Silver layer
    silver_paths = {
        "tracker": f"s3://{bucket}/silver/tracker/date={d}/tracker.parquet",
        "weather": f"s3://{bucket}/silver/weather/date={d}/weather.parquet", 
        "inventory": f"s3://{bucket}/silver/inventory/date={d}/inventory.parquet"
    }
    
    # Load tracker data
    df_tracker = pd.DataFrame()
    if fs.exists(silver_paths["tracker"]):
        df_tracker = pd.read_parquet(silver_paths["tracker"], storage_options=storage_options)
    
    # Load weather data  
    df_weather = pd.DataFrame()
    if fs.exists(silver_paths["weather"]):
        df_weather = pd.read_parquet(silver_paths["weather"], storage_options=storage_options)
    
    # Load inventory data
    df_inventory = pd.DataFrame()
    if fs.exists(silver_paths["inventory"]):
        df_inventory = pd.read_parquet(silver_paths["inventory"], storage_options=storage_options)
    
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
    ctx_path = f"s3://{bucket}/gold/daily_context/date={d}/daily_context.parquet"
    if daily_context:
        pd.DataFrame([daily_context]).to_parquet(ctx_path, index=False, storage_options=storage_options)
        print(f"✅ Gold Daily Context saved: {ctx_path}")
    else:
        ctx_path = None
    
    # Save Recommendation to Gold  
    rec_path = f"s3://{bucket}/gold/recommendation/date={d}/recommendation.parquet"
    if recommendation:
        pd.DataFrame([recommendation]).to_parquet(rec_path, index=False, storage_options=storage_options)
        print(f"✅ Gold Recommendation saved: {rec_path}")
    else:
        rec_path = None
    
    return {
        "daily_context": ctx_path,
        "recommendation": rec_path
    }
