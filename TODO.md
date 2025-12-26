# Data Lake Regeneration Plan

## Current Understanding

- **Source of Truth**: `app.py` defines the correct schema with columns: `Date`, `Day Products`, `Night Products`, `Status`
- **Issue**: `datalake` folder completely deleted, need to regenerate from scratch
- **Current Problem**: `build_silver.py` has imprecise column mapping, `sheets.py` reads from wrong source

## Plan Overview

1. **Fix Sheets Ingestion** - Update `src/ingest/sheets.py` to read from local `journal_history.csv`
2. **Fix Silver Transformation** - Update `src/transform/build_silver.py` with precise column mapping
3. **Create Unified Pipeline** - Create `run_pipeline.py` for immediate execution
4. **Test Pipeline** - Execute and verify data flow

## Detailed Changes Required

### 1. src/ingest/sheets.py

**Current Issue**: Reads from `SHEET_CSV_URL` config variable
**Fix Required**:

- Read from local `journal_history.csv` file
- Handle the exact columns: `Date`, `Day Products`, `Night Products`, `Status`
- Save to bronze layer with proper directory structure

### 2. src/transform/build_silver.py

**Current Issue**: Imprecise column mapping with multiple candidates
**Fix Required**:

- Update `_standardize_tracker_cols()` with exact mapping:
  - `Date` → `tanggal_input`
  - `Day Products` → `produk_pagi`
  - `Night Products` → `produk_malam`
  - `Status` → `status_keamanan`
- Ensure robust directory creation with `os.makedirs` or `pathlib`

### 3. run_pipeline.py (NEW)

**Requirements**:

- Unified script to trigger complete pipeline
- Handle all ingestion sources (sheets, SQL, weather, scraping)
- Execute silver and gold transformations
- Provide clear status feedback
- Handle missing directories gracefully

## Expected Data Flow

```
journal_history.csv → Bronze → Silver → Gold
     ↓                    ↓        ↓       ↓
  Date, Day Products → tanggal_input, produk_pagi → recommendation + context
  Night Products      → produk_malam
  Status              → status_keamanan
```

## Verification Steps

1. Execute `run_pipeline.py`
2. Verify `datalake` folder structure is recreated
3. Check Bronze layer contains CSV files
4. Check Silver layer contains Parquet files with correct schema
5. Verify app.py can read the generated data
