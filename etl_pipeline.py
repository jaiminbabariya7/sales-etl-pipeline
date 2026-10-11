"""
ETL Pipeline: Sales Data Automation
Extracts raw CSV data → Transforms & cleans → Loads to analytics-ready output
"""
import pandas as pd
import numpy as np
import sqlite3
import os
import time
from datetime import datetime

LOG_LINES = []

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    LOG_LINES.append(line)

# ─── EXTRACT ──────────────────────────────────────────────────────────────────
def extract(path):
    log("EXTRACT ▶ Loading raw CSV data...")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Source file not found: {path}")
    df = pd.read_csv(path)
    required_cols = {"order_id", "order_date", "product_name", "quantity", "unit_price",
                     "currency", "region", "sales_rep"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"Source file missing required columns: {missing}")
    log(f"  ✓ Loaded {len(df):,} rows × {len(df.columns)} columns")
    log(f"  ✗ Found {df.isnull().sum().sum()} null values")
    log(f"  ✗ Found {df.duplicated(subset='order_id').sum()} duplicate order_ids")
    log(f"  ✗ Found {(df['quantity'] < 0).sum()} negative quantities")
    return df

# ─── TRANSFORM ────────────────────────────────────────────────────────────────
DATE_FORMATS = ("%m/%d/%Y", "%Y-%m-%d", "%d-%b-%Y")


def parse_date(value: str):
    """Return the date as YYYY-MM-DD, or None if no known format matches."""
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(value.strip(), fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def transform(df):
    log("TRANSFORM ▶ Cleaning and standardizing data...")
    raw_count = len(df)

    # 1. Drop duplicates
    df = df.drop_duplicates(subset="order_id", keep="first")
    log(f"  ✓ Removed {raw_count - len(df)} duplicate records")

    # 2. Drop rows with missing critical fields
    before = len(df)
    df = df[df["order_date"].notna() & (df["order_date"].astype(str).str.strip() != "")]
    log(f"  ✓ Dropped {before - len(df)} rows with missing dates")

    # 3. Parse mixed date formats (MM/DD/YYYY, YYYY-MM-DD, DD-Mon-YYYY) to YYYY-MM-DD
    df["order_date"] = df["order_date"].astype(str).map(parse_date)
    before = len(df)
    df = df.dropna(subset=["order_date"])
    log(f"  ✓ Standardized dates to YYYY-MM-DD ({before - len(df)} unparseable rows dropped)")
    df["order_month"] = pd.to_datetime(df["order_date"]).dt.to_period("M").astype(str)

    # 4. Fix unit_price (remove $ signs, cast to float)
    df["unit_price"] = df["unit_price"].astype(str).str.replace("$", "", regex=False).astype(float)

    # 5. Remove negative quantities
    before = len(df)
    df = df[df["quantity"] > 0]
    log(f"  ✓ Removed {before - len(df)} rows with invalid quantities")

    # 6. Recalculate revenue from clean qty × price (use Decimal-safe multiply then round)
    df["total_revenue"] = (df["quantity"].astype(float) * df["unit_price"]).round(2)

    # 7. Normalize text fields — use str.strip() on product_name to preserve
    #    abbreviations (e.g. "ERP", "CRM") that str.title() would mangle
    df["product_name"] = df["product_name"].str.strip()
    df["sales_rep"] = df["sales_rep"].str.replace("_", " ").str.title().str.strip()

    # 8. FX conversion: normalize EUR/GBP to USD
    fx = {"USD": 1.0, "EUR": 1.08, "GBP": 1.27}
    df["revenue_usd"] = df.apply(
        lambda r: round(r["total_revenue"] * fx.get(r["currency"], 1.0), 2), axis=1
    )

    log(f"  ✓ Normalized currencies to USD (EUR×1.08, GBP×1.27)")
    log(f"  ✓ Clean dataset: {len(df):,} rows ({raw_count - len(df)} removed total)")
    return df

# ─── AGGREGATE ────────────────────────────────────────────────────────────────
def aggregate(df):
    log("AGGREGATE ▶ Building analytics tables...")

    monthly = (df.groupby("order_month")
                 .agg(orders=("order_id", "count"),
                      revenue_usd=("revenue_usd", "sum"),
                      avg_order_value=("revenue_usd", "mean"))
                 .round(2).reset_index())

    by_product = (df.groupby("product_name")
                    .agg(units_sold=("quantity", "sum"),
                         revenue_usd=("revenue_usd", "sum"),
                         orders=("order_id", "count"))
                    .round(2).sort_values("revenue_usd", ascending=False).reset_index())

    by_region = (df.groupby("region")
                   .agg(orders=("order_id", "count"),
                        revenue_usd=("revenue_usd", "sum"))
                   .round(2).reset_index())

    by_rep = (df.groupby("sales_rep")
                .agg(orders=("order_id", "count"),
                     revenue_usd=("revenue_usd", "sum"))
                .round(2).sort_values("revenue_usd", ascending=False).reset_index())

    log(f"  ✓ Monthly summary: {len(monthly)} months")
    log(f"  ✓ Product breakdown: {len(by_product)} products")
    log(f"  ✓ Region breakdown: {len(by_region)} regions")
    log(f"  ✓ Rep performance: {len(by_rep)} sales reps")
    return monthly, by_product, by_region, by_rep

# ─── LOAD ─────────────────────────────────────────────────────────────────────
def load(df, monthly, by_product, by_region, by_rep, out_dir):
    log("LOAD ▶ Writing analytics-ready tables...")
    db_path = os.path.join(out_dir, "analytics.db")
    conn = sqlite3.connect(db_path)

    df.to_sql("fact_sales", conn, if_exists="replace", index=False)
    monthly.to_sql("dim_monthly", conn, if_exists="replace", index=False)
    by_product.to_sql("dim_product", conn, if_exists="replace", index=False)
    by_region.to_sql("dim_region", conn, if_exists="replace", index=False)
    by_rep.to_sql("dim_sales_rep", conn, if_exists="replace", index=False)
    conn.close()

    df.to_csv(os.path.join(out_dir, "clean_sales_data.csv"), index=False)
    monthly.to_csv(os.path.join(out_dir, "monthly_summary.csv"), index=False)
    log(f"  ✓ Loaded 5 tables into analytics database")
    log(f"  ✓ Exported clean CSV: clean_sales_data.csv")
    return db_path

# ─── MAIN ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    OUT_DIR  = os.path.join(BASE_DIR, "output")
    RAW_PATH = os.path.join(BASE_DIR, "raw_sales_data.csv")
    os.makedirs(OUT_DIR, exist_ok=True)

    start = time.time()
    log("=" * 55)
    log("  ETL PIPELINE — Sales Data Automation")
    log("=" * 55)

    raw = extract(RAW_PATH)
    clean = transform(raw)
    monthly, by_product, by_region, by_rep = aggregate(clean)
    db_path = load(clean, monthly, by_product, by_region, by_rep, OUT_DIR)

    elapsed = round(time.time() - start, 2)
    log("=" * 55)
    log(f"  ✅ Pipeline completed in {elapsed}s")
    log(f"  📊 {len(clean):,} clean records ready for analysis")
    log(f"  💰 Total Revenue (USD): ${clean['revenue_usd'].sum():,.0f}")
    log("=" * 55)

    with open(os.path.join(OUT_DIR, "pipeline_run.log"), "w") as f:
        f.write("\n".join(LOG_LINES))
