"""
Generate a synthetic raw sales export (raw_sales_data.csv) with the problems
the pipeline is built to clean: duplicate order IDs from system retries,
missing and mixed-format dates, '$'-prefixed prices, negative quantities from
cancelled lines, and three currencies. Seeded and fully fake.

    python generate_sample_data.py            # 2,000 rows -> raw_sales_data.csv
"""
from __future__ import annotations

import argparse
import csv
import random
from datetime import date, timedelta

PRODUCTS = {  # name: (USD list price, category)
    "Laptop Pro 14": (1450, "Hardware"), "Laptop Air 13": (1100, "Hardware"),
    "27in Monitor": (380, "Hardware"), "Docking Station": (240, "Hardware"),
    "Network Switch 48p": (2200, "Network"), "Wireless Access Point": (420, "Network"),
    "Firewall Appliance": (3900, "Network"), "Rack Server 2U": (8600, "Infrastructure"),
    "Storage Array 24TB": (12500, "Infrastructure"), "UPS 3kVA": (1700, "Infrastructure"),
    "ERP License (annual)": (5200, "Software"), "CRM License (annual)": (2900, "Software"),
    "Endpoint Security (annual)": (65, "Software"), "Office Suite (annual)": (120, "Software"),
}
REGIONS = {"North America": "USD", "Latin America": "USD", "Europe": "EUR",
           "UK & Ireland": "GBP", "Asia Pacific": "USD"}
REPS = ["carol_white", "bob_smith", "emma_brown", "henry_davis", "david_lee",
        "frank_miller", "alice_johnson", "grace_chen"]
DATE_FORMATS = ["%m/%d/%Y"] * 7 + ["%Y-%m-%d"] * 2 + ["%d-%b-%Y"]   # mostly US format


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=int, default=2000)
    ap.add_argument("--out", default="raw_sales_data.csv")
    ap.add_argument("--seed", type=int, default=2024)
    args = ap.parse_args()
    rng = random.Random(args.seed)

    rows = []
    for i in range(1, args.rows + 1):
        if rows and rng.random() < 0.022:                 # system retry -> duplicate order_id
            rows.append(dict(rows[-rng.randint(1, min(20, len(rows)))]))
            continue
        name, (price, _) = rng.choice(list(PRODUCTS.items()))
        region = rng.choice(list(REGIONS))
        currency = REGIONS[region]
        local_price = price / {"USD": 1.0, "EUR": 1.08, "GBP": 1.27}[currency]
        d = date(2024, 1, 1) + timedelta(days=rng.randint(0, 365))
        qty = rng.choices([1, 2, 3, 5, 10, 25], weights=[30, 25, 15, 12, 10, 8])[0]
        if rng.random() < 0.035:                          # cancelled line not voided
            qty = -qty
        unit = round(local_price * rng.uniform(0.9, 1.05), 2)
        rows.append({
            "order_id": f"SO-{100000 + i}",
            "order_date": "" if rng.random() < 0.028 else d.strftime(rng.choice(DATE_FORMATS)),
            "product_name": name,
            "quantity": qty,
            "unit_price": f"${unit}" if rng.random() < 0.4 else unit,
            "currency": currency,
            "region": region,
            "sales_rep": rng.choice(REPS),
        })

    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"{len(rows):,} rows -> {args.out}")


if __name__ == "__main__":
    main()
