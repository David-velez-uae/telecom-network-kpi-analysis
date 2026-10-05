"""Generate a simulated mobile network KPI dataset.

IMPORTANT: all data is synthetic. It does not come from any real operator.

Outputs:
    data/cell_sites.csv   -> one row per cell site
    data/hourly_kpis.csv  -> hourly KPIs per cell for 30 days
"""

from pathlib import Path

import numpy as np
import pandas as pd

SEED = 42
N_CELLS = 40
DAYS = 30
START = "2026-09-01"

rng = np.random.default_rng(SEED)
DATA_DIR = Path(__file__).resolve().parent.parent / "data"

AREAS = {
    "Dubai": ["Downtown", "Marina", "Deira", "Jebel Ali"],
    "Abu Dhabi": ["Corniche", "Khalifa City", "Yas Island"],
    "Sharjah": ["Al Majaz", "Muwaileh"],
}


def build_cell_sites() -> pd.DataFrame:
    rows = []
    for i in range(N_CELLS):
        emirate = str(rng.choice(list(AREAS), p=[0.5, 0.3, 0.2]))
        tech = str(rng.choice(["4G", "5G"], p=[0.55, 0.45]))
        rows.append(
            {
                "cell_id": f"CELL_{i + 1:03d}",
                "emirate": emirate,
                "area": str(rng.choice(AREAS[emirate])),
                "technology": tech,
                "bandwidth_mhz": 100 if tech == "5G" else 20,
                # hidden parameters, used only to simulate behaviour
                "load_factor": float(rng.uniform(0.6, 1.3)),
                "base_rsrp_dbm": float(rng.normal(-88, 7)),
            }
        )
    return pd.DataFrame(rows)


def build_hourly_kpis(sites: pd.DataFrame) -> pd.DataFrame:
    timestamps = pd.date_range(START, periods=DAYS * 24, freq="h")
    hour = timestamps.hour.to_numpy()
    n = len(timestamps)

    # Daily traffic profile: small peak at 13:00, main peak at 20:00
    profile = (
        0.30
        + 0.55 * np.exp(-((hour - 20) ** 2) / 16)
        + 0.25 * np.exp(-((hour - 13) ** 2) / 8)
    )

    frames = []
    for site in sites.itertuples():
        is_5g = site.technology == "5G"
        load = profile * site.load_factor * (1 + rng.normal(0, 0.08, n))
        load = np.clip(load, 0.03, 1.0)

        max_users = 500 if is_5g else 300
        base_tput = 180 if is_5g else 35
        base_lat = 12 if is_5g else 35

        throughput = base_tput * (1.1 - 0.75 * load**2) * (1 + rng.normal(0, 0.05, n))
        latency = base_lat * (1 + 2.5 * load**3) + rng.normal(0, 1.5, n)
        rsrp = site.base_rsrp_dbm + rng.normal(0, 2, n)
        drop_rate = (
            0.3
            + 2.5 * np.clip(load - 0.8, 0, None)
            + 0.08 * np.clip(-100 - rsrp, 0, None)
            + rng.normal(0, 0.1, n)
        )

        frames.append(
            pd.DataFrame(
                {
                    "timestamp": timestamps,
                    "cell_id": site.cell_id,
                    "connected_users": (load * max_users).round().astype(int),
                    "prb_utilization_pct": (load * 100).round(1),
                    "throughput_mbps": np.clip(throughput, 1, None).round(1),
                    "latency_ms": np.clip(latency, 3, None).round(1),
                    "rsrp_dbm": rsrp.round(1),
                    "call_drop_rate_pct": np.clip(drop_rate, 0, None).round(2),
                    "availability_pct": 100.0,
                }
            )
        )
    return pd.concat(frames, ignore_index=True)


def inject_outages(df: pd.DataFrame, n_events: int = 12) -> pd.DataFrame:
    """Simulate random outages of 2-6 hours on random cells."""
    timestamps = df["timestamp"].drop_duplicates().reset_index(drop=True)
    cells = df["cell_id"].unique()
    for _ in range(n_events):
        cell = rng.choice(cells)
        start = int(rng.integers(0, len(timestamps) - 8))
        duration = int(rng.integers(2, 7))
        window = timestamps.iloc[start : start + duration]
        mask = (df["cell_id"] == cell) & (df["timestamp"].isin(window))
        df.loc[mask, "availability_pct"] = round(float(rng.uniform(0, 60)), 1)
        df.loc[mask, ["connected_users", "throughput_mbps"]] = 0
    return df


def main() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    sites = build_cell_sites()
    kpis = inject_outages(build_hourly_kpis(sites))

    sites.drop(columns=["load_factor", "base_rsrp_dbm"]).to_csv(
        DATA_DIR / "cell_sites.csv", index=False
    )
    kpis.to_csv(DATA_DIR / "hourly_kpis.csv", index=False)

    print(f"Cell sites: {len(sites)}")
    print(f"KPI rows:   {len(kpis)}")
    print(kpis.head())


if __name__ == "__main__":
    main()