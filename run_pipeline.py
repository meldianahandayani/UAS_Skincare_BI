#!/usr/bin/env python3
"""
Unified Data Lake Regeneration Pipeline
======================================

This script regenerates the complete Data Lake (Bronze, Silver, Gold) from scratch.
Run this script to rebuild all data layers immediately after deleting the datalake folder.

Usage:
    python run_pipeline.py

Or with custom coordinates:
    python run_pipeline.py --lat -6.2088 --lon 106.8456
"""

import argparse
import sys
from datetime import date
from pathlib import Path

# Add src to Python path for imports
sys.path.append(str(Path(__file__).parent / "src"))

# Import all pipeline components
from ingest.inventory import run as ingest_inventory
from ingest.sheets import run as ingest_sheets
from ingest.weather import run as ingest_weather
from ingest.scrape_ingredients import run as ingest_scrape
from transform.build_silver import run as build_silver
from transform.build_gold import run as build_gold
from utils.config import DB_URL, OWM_API_KEY, LAT, LON


def print_header(title: str):
    """Print a formatted header"""
    print(f"\n{'='*60}")
    print(f"🚀 {title}")
    print(f"{'='*60}")


def print_step(step_num: int, description: str):
    """Print a formatted step"""
    print(f"\n📍 Step {step_num}: {description}")
    print("-" * 40)


def run_complete_pipeline(lat: float = None, lon: float = None) -> dict:
    """
    Execute the complete data pipeline from scratch.
    
    Args:
        lat: Latitude for weather data (optional)
        lon: Longitude for weather data (optional)
    
    Returns:
        dict: Summary of pipeline execution results
    """
    today = date.today()
    
    # Use provided coordinates or fall back to config/defaults
    if lat is None or lon is None:
        try:
            lat = float(LAT) if LAT else -6.2088  # Default: Jakarta
            lon = float(LON) if LON else 106.8456
            print(f"📍 Using coordinates: {lat}, {lon}")
        except (ValueError, TypeError):
            lat, lon = -6.2088, 106.8458  # Fallback coordinates
            print(f"📍 Using default coordinates: {lat}, {lon}")
    
    results = {
        "date": str(today),
        "location": f"{lat},{lon}",
        "status": "success",
        "bronze": {},
        "silver": {},
        "gold": {},
        "errors": []
    }
    
    try:
        print_header("DATA LAKE REGENERATION PIPELINE")
        print(f"📅 Target Date: {today}")
        print(f"🔧 Data Source: journal_history.csv (app.py schema)")
        print(f"🗄️  Database: {'Connected' if DB_URL else 'Not Configured'}")
        print(f"🌤️  Weather API: {'Available' if OWM_API_KEY else 'Not Available'}")
        
        # =========================================================
        # BRONZE LAYER - Raw Data Ingestion
        # =========================================================
        print_step(1, "BRONZE LAYER - Raw Data Ingestion")
        
        # 1.1 Inventory (PostgreSQL)
        try:
            print("📦 Ingesting inventory from PostgreSQL...")
            inv_path = ingest_inventory(today)
            results["bronze"]["inventory"] = inv_path
            print(f"   ✅ Inventory saved: {inv_path}")
        except Exception as e:
            error_msg = f"Inventory ingestion failed: {e}"
            print(f"   ❌ {error_msg}")
            results["errors"].append(error_msg)
        
        # 1.2 Journal/Tracker (CSV)
        try:
            print("📊 Ingesting journal tracker from CSV...")
            sheets_path = ingest_sheets(today)
            results["bronze"]["tracker"] = sheets_path
            print(f"   ✅ Tracker saved: {sheets_path}")
        except Exception as e:
            error_msg = f"Tracker ingestion failed: {e}"
            print(f"   ❌ {error_msg}")
            results["errors"].append(error_msg)
        
        # 1.3 Weather (OpenWeatherMap)
        try:
            print("🌤️ Ingesting weather data...")
            weather_path = ingest_weather(today, lat=lat, lon=lon)
            results["bronze"]["weather"] = weather_path
            print(f"   ✅ Weather saved: {weather_path}")
        except Exception as e:
            error_msg = f"Weather ingestion failed: {e}"
            print(f"   ❌ {error_msg}")
            results["errors"].append(error_msg)
        
        # 1.4 Ingredients (CosDNA Scraping)
        try:
            print("🧪 Scraping ingredients data...")
            ingredients_df = ingest_scrape(today, pages_csv_path="sources/product_pages.csv")
            results["bronze"]["ingredients"] = f"{len(ingredients_df)} products scraped"
            print(f"   ✅ Ingredients scraped: {len(ingredients_df)} products")
        except Exception as e:
            error_msg = f"Ingredient scraping failed: {e}"
            print(f"   ❌ {error_msg}")
            results["errors"].append(error_msg)
        
        # =========================================================
        # SILVER LAYER - Data Cleaning & Standardization
        # =========================================================
        print_step(2, "SILVER LAYER - Data Transformation")
        
        try:
            print("🔄 Building Silver layer with standardized schema...")
            silver_results = build_silver(today)
            results["silver"] = silver_results
            
            for key, path in silver_results.items():
                if path != "Not Found":
                    print(f"   ✅ {key.capitalize()}: {path}")
                else:
                    print(f"   ⚠️  {key.capitalize()}: Data not found")
            
        except Exception as e:
            error_msg = f"Silver layer build failed: {e}"
            print(f"   ❌ {error_msg}")
            results["errors"].append(error_msg)
            results["status"] = "partial"
        
        # =========================================================
        # GOLD LAYER - Business Logic & Recommendations
        # =========================================================
        print_step(3, "GOLD LAYER - Business Intelligence")
        
        try:
            print("🏆 Building Gold layer with recommendations...")
            gold_results = build_gold(today, ingredients_df if 'ingredients_df' in locals() else None)
            results["gold"] = gold_results
            
            for key, path in gold_results.items():
                if path != "Not Found":
                    print(f"   ✅ {key.capitalize()}: {path}")
                else:
                    print(f"   ⚠️  {key.capitalize()}: Data not found")
                    
        except Exception as e:
            error_msg = f"Gold layer build failed: {e}"
            print(f"   ❌ {error_msg}")
            results["errors"].append(error_msg)
            results["status"] = "partial"
        
        # =========================================================
        # PIPELINE SUMMARY
        # =========================================================
        print_header("PIPELINE EXECUTION SUMMARY")
        
        total_bronze = len([v for v in results["bronze"].values() if v and v != "Not Found"])
        total_silver = len([v for v in results["silver"].values() if v and v != "Not Found"])
        total_gold = len([v for v in results["gold"].values() if v and v != "Not Found"])
        
        print(f"📊 Bronze Layer: {total_bronze}/4 sources ingested")
        print(f"🔄 Silver Layer: {total_silver}/4 datasets processed")
        print(f"🏆 Gold Layer: {total_gold}/2 datasets generated")
        print(f"❌ Errors: {len(results['errors'])}")
        
        if results["errors"]:
            print(f"\n⚠️  ISSUES ENCOUNTERED:")
            for i, error in enumerate(results["errors"], 1):
                print(f"   {i}. {error}")
        
        if total_bronze >= 2 and total_silver >= 2:  # At least basic data processing
            print(f"\n🎉 DATA LAKE REGENERATION COMPLETE!")
            print(f"📁 Data saved in: ./datalake/{today}/")
            print(f"💡 You can now run your Streamlit app: streamlit run app.py")
        else:
            print(f"\n⚠️  REGENERATION INCOMPLETE - Check errors above")
            results["status"] = "failed"
        
        return results
        
    except Exception as e:
        error_msg = f"Pipeline execution failed: {e}"
        print(f"❌ {error_msg}")
        results["status"] = "failed"
        results["errors"].append(error_msg)
        return results


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Regenerate Data Lake from scratch",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_pipeline.py                     # Use default coordinates
  python run_pipeline.py --lat -6.2088 --lon 106.8456  # Jakarta
  python run_pipeline.py --help              # Show this help
        """
    )
    
    parser.add_argument(
        "--lat", 
        type=float, 
        help="Latitude for weather data (default: from config or -6.2088)"
    )
    
    parser.add_argument(
        "--lon", 
        type=float, 
        help="Longitude for weather data (default: from config or 106.8456)"
    )
    
    args = parser.parse_args()
    
    # Run the pipeline
    results = run_complete_pipeline(lat=args.lat, lon=args.lon)
    
    # Exit with appropriate code
    if results["status"] == "success":
        sys.exit(0)
    elif results["status"] == "partial":
        print("\n⚠️  Pipeline completed with warnings")
        sys.exit(1)
    else:
        print("\n❌ Pipeline failed")
        sys.exit(2)


if __name__ == "__main__":
    main()
