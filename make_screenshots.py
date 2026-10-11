"""
Render the README screenshots from a real pipeline run:
    python generate_sample_data.py && python etl_pipeline.py && python make_screenshots.py

Reads output/analytics.db, raw_sales_data.csv and output/pipeline_run.log.
"""
import os
import sqlite3

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.patches import FancyBboxPatch

BG, PANEL, FG, MUTED = "#0d1117", "#161b22", "#e6edf3", "#8b949e"
ACCENTS = ["#58a6ff", "#3fb950", "#d29922", "#bc8cff", "#ff7b72", "#39c5cf", "#f778ba", "#e3b341"]
OUT = "screenshots"
plt.rcParams.update({"text.color": FG, "axes.labelcolor": MUTED, "xtick.color": MUTED,
                     "ytick.color": MUTED, "axes.edgecolor": "#30363d", "font.size": 10})


def panel(ax, title):
    ax.set_facecolor(PANEL)
    ax.set_title(title, color=FG, fontsize=11, loc="left", pad=8)
    for s in ax.spines.values():
        s.set_color("#30363d")


def dashboard(conn):
    fact = pd.read_sql("SELECT * FROM fact_sales", conn)
    monthly = pd.read_sql("SELECT * FROM dim_monthly ORDER BY order_month", conn)
    product = pd.read_sql("SELECT * FROM dim_product ORDER BY revenue_usd DESC", conn)
    region = pd.read_sql("SELECT * FROM dim_region ORDER BY revenue_usd DESC", conn)
    rep = pd.read_sql("SELECT * FROM dim_sales_rep ORDER BY revenue_usd DESC", conn)

    fig = plt.figure(figsize=(16, 9), facecolor=BG)
    fig.suptitle("Sales Analytics Dashboard", fontsize=18, color=FG, y=0.97)
    fig.text(0.5, 0.925, "ETL output (synthetic data) · FY 2024 · Python + pandas + SQLite",
             ha="center", color=MUTED)
    kpis = [("Total Revenue (USD)", f"${fact.revenue_usd.sum():,.0f}"),
            ("Clean Orders", f"{len(fact):,}"),
            ("Avg Order Value (USD)", f"${fact.revenue_usd.mean():,.0f}"),
            ("Top Product", product.product_name.iloc[0])]
    for i, (label, value) in enumerate(kpis):
        ax = fig.add_axes([0.04 + i * 0.24, 0.76, 0.21, 0.12]); ax.axis("off")
        ax.add_patch(FancyBboxPatch((0, 0), 1, 1, boxstyle="round,pad=0.02",
                                    fc=PANEL, ec=ACCENTS[i], lw=1.5, transform=ax.transAxes))
        ax.text(0.5, 0.58, value, ha="center", fontsize=17 if i < 3 else 13,
                color=ACCENTS[i], weight="bold")
        ax.text(0.5, 0.22, label, ha="center", color=MUTED)

    ax = fig.add_axes([0.05, 0.42, 0.55, 0.28]); panel(ax, "Monthly Revenue (USD)")
    ax.plot(monthly.order_month.str[5:], monthly.revenue_usd / 1e6, color=ACCENTS[1], marker="o")
    ax.fill_between(range(len(monthly)), monthly.revenue_usd / 1e6, color=ACCENTS[1], alpha=0.15)
    ax.set_ylabel("$ millions")

    ax = fig.add_axes([0.66, 0.42, 0.3, 0.28]); ax.set_facecolor(BG)
    ax.set_title("Revenue by Region", color=FG, fontsize=11)
    ax.pie(region.revenue_usd, labels=region.region, colors=ACCENTS[:len(region)],
           autopct="%1.0f%%", textprops={"color": FG, "fontsize": 8},
           wedgeprops={"linewidth": 1, "edgecolor": BG})

    ax = fig.add_axes([0.13, 0.06, 0.4, 0.28]); panel(ax, "Top 5 Products by Revenue (USD)")
    top = product.head(5).iloc[::-1]
    ax.barh(top.product_name, top.revenue_usd / 1e6, color=ACCENTS[:5][::-1])
    ax.set_xlabel("$ millions")

    ax = fig.add_axes([0.62, 0.06, 0.34, 0.28]); panel(ax, "Sales Rep Leaderboard (USD)")
    ax.axis("off")
    for i, r in enumerate(rep.head(8).itertuples()):
        y = 0.9 - i * 0.115
        ax.text(0.04, y, f"{i + 1}. {r.sales_rep}", transform=ax.transAxes, color=FG)
        ax.text(0.96, y, f"${r.revenue_usd:,.0f}", transform=ax.transAxes, ha="right", color=ACCENTS[1])
    fig.savefig(f"{OUT}/01_executive_dashboard.png", dpi=150, facecolor=BG)
    plt.close(fig)


def quality(raw, fact):
    dates = raw.order_date.fillna("").astype(str).str.strip()
    before = {"Duplicate order IDs": int(raw.duplicated(subset="order_id").sum()),
              "Missing dates": int((dates == "").sum()),
              "Negative quantities": int((raw.quantity < 0).sum())}
    after = {"Duplicate order IDs": int(fact.duplicated(subset="order_id").sum()),
             "Missing dates": int(fact.order_date.isna().sum()),
             "Negative quantities": int((fact.quantity < 0).sum())}
    fig, axes = plt.subplots(1, 3, figsize=(16, 5.6), facecolor=BG)
    fig.suptitle("Data Quality: Raw Export vs Clean Output", fontsize=16, color=FG)
    for ax, (name, b), color in zip(axes, before.items(), [ACCENTS[4], ACCENTS[2], ACCENTS[3]]):
        panel(ax, name)
        bars = ax.bar(["Raw export", "After ETL"], [b, after[name]], color=[color, ACCENTS[1]])
        for bar in bars:
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(), f"{int(bar.get_height())}",
                    ha="center", va="bottom", color=FG, weight="bold")
    fig.text(0.5, 0.02, f"Raw rows: {len(raw):,}  →  clean rows: {len(fact):,}  "
             f"({len(raw) - len(fact)} removed)", ha="center", color=MUTED)
    fig.savefig(f"{OUT}/02_data_quality_report.png", dpi=150, facecolor=BG)
    plt.close(fig)


def architecture(raw, fact):
    fig = plt.figure(figsize=(16, 6.5), facecolor=BG)
    ax = fig.add_axes([0, 0, 1, 1]); ax.axis("off"); ax.set_xlim(0, 16); ax.set_ylim(0, 6.5)
    ax.text(8, 6.0, "ETL Pipeline Architecture", ha="center", fontsize=18, color=FG)
    ax.text(8, 5.55, "Python · pandas · SQLite  (single script: etl_pipeline.py)",
            ha="center", color=MUTED)
    steps = [("Raw CSV export", "3 regional CRMs\nUSD / EUR / GBP"),
             ("Extract", "load + profile\nnulls, dupes, negatives"),
             ("Transform", "dedupe, parse dates,\nstrip $, drop cancels,\nFX to USD"),
             ("Aggregate", "monthly, product,\nregion, sales rep"),
             ("Load", "SQLite analytics.db\n(1 fact + 4 summaries)\n+ clean CSV")]
    for i, (title, body) in enumerate(steps):
        x = 0.5 + i * 3.1
        ax.add_patch(FancyBboxPatch((x, 2.0), 2.5, 2.6, boxstyle="round,pad=0.08",
                                    fc=PANEL, ec=ACCENTS[i], lw=2))
        ax.text(x + 1.25, 4.15, title, ha="center", color=ACCENTS[i], fontsize=13, weight="bold")
        ax.text(x + 1.25, 3.0, body, ha="center", va="center", color=FG, fontsize=10)
        if i < len(steps) - 1:
            ax.annotate("", xy=(x + 3.05, 3.3), xytext=(x + 2.6, 3.3),
                        arrowprops={"arrowstyle": "->", "color": MUTED, "lw": 1.8})
    ax.text(8, 1.1, f"Sample run: {len(raw):,} raw rows → {len(fact):,} clean rows · "
            f"${fact.revenue_usd.sum():,.0f} total revenue (USD)", ha="center", color=MUTED, fontsize=11)
    fig.savefig(f"{OUT}/03_pipeline_architecture.png", dpi=150, facecolor=BG)
    plt.close(fig)


def terminal_log():
    lines = open("output/pipeline_run.log", encoding="utf-8").read().splitlines()
    fig = plt.figure(figsize=(12, 0.32 * len(lines) + 1.2), facecolor=BG)
    ax = fig.add_axes([0, 0, 1, 1]); ax.axis("off")
    ax.text(0.02, 0.97, "$ python etl_pipeline.py", color=ACCENTS[1], family="monospace",
            fontsize=11, transform=ax.transAxes, va="top")
    step = 0.92 / max(len(lines), 1)
    for i, line in enumerate(lines):
        color = ACCENTS[4] if "✗" in line else ACCENTS[1] if "✓" in line else FG
        clean = line.replace("✓", "+").replace("✗", "!").replace("▶", ">").replace("✅", "").replace(
            "📊", "").replace("💰", "")
        ax.text(0.02, 0.93 - i * step, clean, color=color, family="monospace", fontsize=10,
                transform=ax.transAxes, va="top")
    fig.savefig(f"{OUT}/04_pipeline_terminal_log.png", dpi=150, facecolor=BG)
    plt.close(fig)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    conn = sqlite3.connect("output/analytics.db")
    raw = pd.read_csv("raw_sales_data.csv")
    fact = pd.read_sql("SELECT * FROM fact_sales", conn)
    dashboard(conn)
    quality(raw, fact)
    architecture(raw, fact)
    terminal_log()
    conn.close()
    print("screenshots written to", OUT)
