import os
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv("DB_URL")
SHEET_CSV_URL = os.getenv("SHEET_CSV_URL")

OWM_API_KEY = os.getenv("OWM_API_KEY")
LAT = os.getenv("LAT")
LON = os.getenv("LON")
UNITS = os.getenv("UNITS", "metric")