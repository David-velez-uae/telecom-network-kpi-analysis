"""Load the synthetic CSV files into a SQLite database."""

import sqlite3
from pathlib import Path

import pandas as pd

DATA = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DATA / "network.db"

SCHEMA = """
DROP TABLE IF EXISTS hourly_kpis;
DROP TABLE IF EXISTS cell_sites;

CREATE TABLE cell_sites (
    cell_id        TEXT PRIMARY KEY,
    emirate        TEXT NOT NULL,
    area           TEXT NOT NULL,
    technology     TEXT NOT NULL CHECK (technology IN ('4G', '5G')),
    bandwidth_mhz  INTEGER NOT NULL
);

CREATE TABLE hourly_kpis (
    timestamp            TEXT NOT NULL,
    cell_id              TEXT NOT NULL REFERENCES cell_sites(cell_id),
    connected_users      INTEGER NOT NULL,
    prb_utilization_pct  REAL NOT NULL,
    throughput_mbps      REAL NOT NULL,
    latency_ms           REAL NOT NULL,
    rsrp_dbm             REAL NOT NULL,
    call_drop_rate_pct   REAL NOT NULL,
    availability_pct     REAL NOT NULL,
    PRIMARY KEY (timestamp, cell_id)
);

CREATE INDEX idx_kpis_cell ON hourly_kpis(cell_id);
"""


def main() -> None:
    sites = pd.read_csv(DATA / "cell_sites.csv")
    kpis = pd.read_csv(DATA / "hourly_kpis.csv")

    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)
    sites.to_sql("cell_sites", conn, if_exists="append", index=False)
    kpis.to_sql("hourly_kpis", conn, if_exists="append", index=False, chunksize=5000)
    conn.commit()

    for table in ("cell_sites", "hourly_kpis"):
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"{table}: {count} rows")
    conn.close()


if __name__ == "__main__":
    main()