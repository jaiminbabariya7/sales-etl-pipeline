# Sales Data ETL Pipeline

**Scenario:** B2B enterprise IT hardware & software distributor (synthetic sample data; no real client data)  
**Scope:** Automated ETL pipeline — raw multi-currency sales exports → clean analytical database  
**Engineer:** Jaimin Babariya (Data Engineer)

---

## Business Problem

The scenario models a distributor of enterprise IT products (network hardware, ERP/CRM licenses, server infrastructure) across five global regions. Its sales team exported orders from three regional CRM systems (USD, EUR, GBP) with inconsistent formatting — mixed date formats, duplicate order IDs from system retries, and negative quantities from cancelled lines not being voided correctly. Finance needed a single clean dataset for monthly reporting without manual Excel cleanup.

This pipeline automates the full Extract → Transform → Load cycle and produces a normalized analytics database ready for BI tooling.

---

## What It Does

**Extract** — reads raw CSV export from source system, logs row count and data quality issues upfront.

**Transform:**
- Deduplicates on `order_id` (keeps first occurrence)
- Drops rows with missing or unparseable `order_date`
- Standardizes dates to `YYYY-MM-DD`
- Strips `$` symbols from `unit_price` and casts to float
- Removes negative-quantity lines (cancelled orders)
- Recalculates `total_revenue = quantity × unit_price`
- Normalizes all revenue to USD using fixed FX rates (EUR×1.08, GBP×1.27)

**Aggregate** — builds four dimension tables: monthly summary, product breakdown, region breakdown, sales rep performance.

**Load** — writes all five tables (1 fact + 4 dims) to SQLite analytics database. Exports clean CSV alongside.

---

## Output

| File | Description |
|---|---|
| `output/analytics.db` | SQLite database with 5 tables (fact_sales, dim_monthly, dim_product, dim_region, dim_sales_rep) |
| `output/clean_sales_data.csv` | Fully cleaned and normalized flat file |
| `output/monthly_summary.csv` | Month-level revenue and order count aggregation |
| `output/pipeline_run.log` | Timestamped run log with before/after row counts |

---

## Pipeline Results

```
Loaded:    2,000 raw rows
Cleaned:   1,828 rows (172 removed)
  - 44 duplicate order_ids removed
  - 57 rows with missing dates dropped
  - 71 negative-quantity lines removed
Total Revenue (USD): $50,023,325
```

---

## Project Structure

```
etl_pipeline_project/
├── etl_pipeline.py         # Main ETL script (Extract → Transform → Aggregate → Load)
├── raw_sales_data.csv      # Source data export
├── requirements.txt
├── output/
│   ├── analytics.db        # Analytics-ready SQLite database
│   ├── clean_sales_data.csv
│   ├── monthly_summary.csv
│   └── pipeline_run.log
└── screenshots/
    ├── 01_executive_dashboard.png
    ├── 02_data_quality_report.png
    ├── 03_pipeline_architecture.png
    └── 04_pipeline_terminal_log.png
```

---

## Running Locally

```bash
pip install -r requirements.txt
python etl_pipeline.py
```

Expects `raw_sales_data.csv` in the project root. Output is written to `output/`.
