"""Build the slim Parquet files the app reads.

Input : the raw Olist CSVs (see README for where to get them).
Output: data/leads.parquet, data/deals.parquet, data/sales.parquet

Only rows and columns the analysis needs are kept, so the repo stays small.
Usage: python scripts/build_data.py <dir_with_funnel_csvs> <dir_with_ecommerce_csvs>
"""
import sys
from pathlib import Path

import duckdb

funnel_dir, shop_dir = Path(sys.argv[1]), Path(sys.argv[2])
out = Path(__file__).resolve().parents[1] / "data"
out.mkdir(exist_ok=True)
con = duckdb.connect()

con.execute(f"""
    COPY (
        SELECT mql_id,
               first_contact_date,
               landing_page_id,
               COALESCE(origin, 'unknown') AS origin
        FROM read_csv_auto('{funnel_dir / "olist_marketing_qualified_leads_dataset.csv"}')
    ) TO '{out / "leads.parquet"}' (FORMAT parquet)
""")

con.execute(f"""
    COPY (
        SELECT mql_id, seller_id, sdr_id, sr_id,
               CAST(won_date AS DATE) AS won_date,
               business_segment, lead_type, business_type
        FROM read_csv_auto('{funnel_dir / "olist_closed_deals_dataset.csv"}')
    ) TO '{out / "deals.parquet"}' (FORMAT parquet)
""")

# One row per order item sold by a seller that came through the funnel.
# Cancelled and unavailable orders are not revenue, so they are dropped here.
con.execute(f"""
    COPY (
        SELECT i.seller_id,
               i.order_id,
               CAST(o.order_purchase_timestamp AS DATE) AS order_date,
               i.price
        FROM read_csv_auto('{shop_dir / "olist_order_items_dataset.csv"}') i
        JOIN read_csv_auto('{shop_dir / "olist_orders_dataset.csv"}') o USING (order_id)
        WHERE o.order_status NOT IN ('canceled', 'unavailable')
          AND i.seller_id IN (
              SELECT seller_id
              FROM read_csv_auto('{funnel_dir / "olist_closed_deals_dataset.csv"}'))
    ) TO '{out / "sales.parquet"}' (FORMAT parquet)
""")

for name in ("leads", "deals", "sales"):
    n = con.execute(f"SELECT count(*) FROM '{out / (name + '.parquet')}'").fetchone()[0]
    print(f"{name:6s} {n:>6,} rows")
