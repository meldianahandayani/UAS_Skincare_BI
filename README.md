# Skincare BI - Airflow Implementation Guide

## 🎯 Overview

This implementation provides a complete Apache Airflow setup for your skincare tracking system, handling all data operations in a single DAG.

## 📁 Files Created

### Core Airflow Files

- `dags/airflow_dag.py` - Main DAG with all data operations
- `docker-compose.yml` - Updated with Airflow services
- `.env` - Environment configuration
- `requirements.txt` - Python dependencies
- `start_airflow.sh` - Startup script

### Directory Structure

```
c:/Dev/UAS_Skincare_BI/
├── dags/              # Airflow DAGs directory
├── logs/              # Airflow logs
├── config/            # Airflow configuration
├── plugins/           # Custom Airflow plugins
├── data_source/       # Your existing data
├── sql/               # Database schema
├── datalake/          # Bronze/Silver/Gold layers (auto-created)
└── app.py             # Your existing Streamlit app
```

## 🔧 Features Implemented

### Data Collection Tasks

1. **Weather API Integration** - OpenWeatherMap data fetching
2. **Database Operations** - PostgreSQL inventory management
3. **CosDNA Web Scraping** - Ingredient analysis
4. **Journal History** - CSV-based tracking data

### Data Processing Pipeline

- **Bronze Layer**: Raw data collection
- **Silver Layer**: Cleaned and processed data
- **Gold Layer**: Business intelligence and recommendations

### AI-Powered Features

- Routine conflict detection
- Weather-based recommendations
- Safety scoring system
- Personalized AM/PM routines

## 🚀 Quick Start

### 1. Setup Environment

```bash
# Make script executable (Linux/Mac)
chmod +x start_airflow.sh

# Start all services
./start_airflow.sh
```

### 2. Access Airflow UI

- **URL**: http://localhost:8080
- **Username**: admin
- **Password**: admin

### 3. Configure API Keys

1. Go to Airflow Admin → Variables
2. Add your OpenWeatherMap API key:
   - Key: `owm_api_key`
   - Value: `your_actual_api_key`

### 4. Trigger DAG

1. Find "skincare_complete_pipeline" DAG
2. Click "Trigger DAG"
3. Monitor execution in Airflow UI

## 📊 Pipeline Flow

```
Data Collection (Parallel)
├── Weather API → Silver Weather
├── Database → Silver Inventory
├── CosDNA → Silver Ingredients
└── Journal → Silver Tracker

Silver Processing (Sequential)
├── Daily Context Creation
└── Recommendation Engine

Gold Layer Creation
├── Gold Context (Business Intelligence)
└── Gold Recommendations (Personalized Routines)

Cleanup & Monitoring
└── Temporary File Cleanup
```

## 🔍 Monitoring & Troubleshooting

### Check Service Status

```bash
docker-compose ps
```

### View Logs

```bash
# Webserver logs
docker-compose logs airflow-webserver

# Scheduler logs
docker-compose logs airflow-scheduler

# Worker logs
docker-compose logs airflow-worker
```

### Common Issues

1. **Permission Errors**:

   - On Windows, ignore chmod errors - script will still work

2. **API Rate Limits**:

   - CosDNA scraping is limited to first 10 products per run
   - Add delays between requests

3. **Database Connection**:

   - Ensure PostgreSQL is running: `docker-compose ps`
   - Check connection in Airflow Admin → Connections

4. **Missing Data**:
   - Check `/opt/airflow/logs/` for detailed error logs
   - Verify API keys are set correctly

## 🔧 Customization

### Adjust Scraping Limits

Edit `dags/airflow_dag.py`:

```python
# Line ~280: Limit products to scrape
for idx, row in inventory_data.head(10).iterrows():
```

### Change Schedule

Edit DAG definition:

```python
dag = DAG(
    'skincare_complete_pipeline',
    schedule_interval='@daily',  # Change to '@hourly', '@weekly', etc.
    ...
)
```

### Modify Data Paths

Update `get_data_paths()` function in the DAG for custom storage locations.

## 📈 Performance Notes

- **Concurrent Tasks**: Data collection runs in parallel for efficiency
- **Error Handling**: Comprehensive try/catch with fallback values
- **Resource Management**: Automatic cleanup of temporary files
- **Monitoring**: Detailed logging at each pipeline stage

## 🛡️ Security Considerations

- API keys stored in Airflow Variables (secure)
- Database credentials in environment variables
- Web scraping includes delays to respect server resources
- No sensitive data logged in plain text

## 📝 Next Steps

1. **Test the pipeline** with a small dataset
2. **Monitor execution** in Airflow UI
3. **Integrate with your Streamlit app** by reading from the data lake
4. **Add email notifications** for failures
5. **Scale up** CosDNA scraping as needed

Your complete skincare BI pipeline is now ready for production use!
