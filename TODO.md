# Skincare BI Pipeline Migration: Local → Airflow + MinIO

## Migration Plan Overview

Migrate existing Skincare BI pipeline from local storage to Apache Airflow + MinIO (S3-compatible) while preserving all existing functionality and business logic.

## Current Architecture Analysis

- **Current Storage**: Local filesystem (`datalake/bronze/silver/gold`)
- **Pipeline Orchestration**: Sequential Python script (`src/pipeline.py`)
- **Database**: PostgreSQL for inventory data
- **Frontend**: Streamlit app
- **Data Flow**: inventory → sheets → weather → scrape → silver → gold

## Implementation Steps

### Phase 1: Infrastructure Setup

- [ ] 1.1 Add Airflow services to docker-compose.yml
- [ ] 1.2 Add MinIO service for S3-compatible storage
- [ ] 1.3 Update requirements.txt with Airflow + MinIO dependencies
- [ ] 1.4 Configure environment variables for Airflow and MinIO

### Phase 2: Storage Layer Migration

- [ ] 2.1 Create new MinIO-based paths utility (`src/utils/s3_paths.py`)
- [ ] 2.2 Update existing path utilities to support both local and S3
- [ ] 2.3 Test S3 integration with sample data

### Phase 3: Airflow DAG Creation

- [ ] 3.1 Create Airflow DAG that mirrors current pipeline logic
- [ ] 3.2 Implement task dependencies and retry logic
- [ ] 3.3 Add monitoring and alerting
- [ ] 3.4 Configure connection to MinIO

### Phase 4: Code Updates

- [ ] 4.1 Update all ingestion modules to use S3 paths
- [ ] 4.2 Update transform modules to use S3 paths
- [ ] 4.3 Preserve all existing business logic
- [ ] 4.4 Update configuration management

### Phase 5: Testing & Validation

- [ ] 5.1 Test full pipeline execution
- [ ] 5.2 Validate data integrity between old and new pipeline
- [ ] 5.3 Test monitoring and alerting
- [ ] 5.4 Create documentation

## Technical Specifications

- **Airflow Version**: 2.8+ (latest stable)
- **MinIO Version**: Latest stable
- **Storage Format**: Maintain Parquet for processed data
- **Scheduling**: Daily runs with manual trigger capability
- **Monitoring**: Airflow UI + logging

## Files to Create/Modify

- `docker-compose.yml` (add Airflow + MinIO services)
- `requirements.txt` (add dependencies)
- `src/utils/s3_paths.py` (new MinIO paths utility)
- `airflow/dags/skincare_pipeline.py` (new Airflow DAG)
- `airflow/config/` (Airflow configuration)
- Environment variables for all services

## Success Criteria

- [ ] Pipeline executes successfully via Airflow
- [ ] Data stored in MinIO with proper structure
- [ ] All existing functionality preserved
- [ ] Monitoring and alerting working
- [ ] Documentation complete
