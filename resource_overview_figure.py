"""
resource_overview_figure.py

Standalone script: builds a 4-panel resource overview figure (wave, tidal,
wind, demand) for 2019, and saves it to DATA/outputs/figures/.

Data loading reuses the SAME logic already validated in
preliminary_renewable_only_balance.py -- including the wind turbine-count
replication fix (each WindTurbine_N.csv represents ONE turbine, replicated
per site's actual turbine count to match base_model.py) and the robust
datetime parser (falls back from day-first to month-first parsing per
file, since different input files in this project use different date
conventions). Reusing this logic here avoids reintroducing either bug.
"""

import glob
import os
import warnings

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# ==============================================================================
# CONSTANTS
# ==============================================================================

INPUT_DIR = "DATA/inputs"
OUTPUT_DIR = "DATA/outputs/figures"

LOAD_PROFILE_FILE = f"{INPUT_DIR}/Load_Profile.csv"
TIDAL_PROFILE_FILE = f"{INPUT_DIR}/tidal_orkney_2019.csv"
WAVE_PROFILE_FILE = f"{INPUT_DIR}/wave_orkney_2019.csv"
WIND_FILE_PATTERN = f"{INPUT_DIR}/WindTurbine_*.csv"

EXPECTED_HOURS = 8760
TOTAL_WIND_CAPACITY_MW = 55.4  # for converting wind MW -> wind per-unit

# Per-site turbine counts, confirmed directly against the base network's
# generator list (see check_network_wind_representation.py) -- each
# WindTurbine_N.csv represents ONE turbine's profile, replicated by this
# count to match base_model.py's per-site generator replication.
TURBINE_COUNT_PER_SITE = {
    "WindTurbine_3": 2,
    "WindTurbine_4": 2,
    "WindTurbine_5": 5,    # Hammers Hill
    "WindTurbine_12": 5,   # Spurness
    "WindTurbine_16": 3,
}

# Plot colours -- consistent with the wave/tidal/wind/demand convention
# used throughout the rest of this project (wave = amber, tidal = green,
# wind = blue, demand = dark grey/black).
C_WAVE = "#e8a33d"
C_TIDAL = "#4a7c3f"
C_WIND = "#7fa8d9"
C_DEMAND = "#333333"


# ==============================================================================
# DATA LOADING (reused, validated logic)
# ==============================================================================

def find_datetime_column(df, filename=""):
    candidates = [c for c in df.columns if str(c).strip().lower() in
                  ("datetime", "date_time", "date", "timestamp", "time")]
    if candidates:
        return candidates[0]
    warnings.warn(f"No obviously-named DateTime column found in {filename}; "
                   f"falling back to first column '{df.columns[0]}'. Verify this is correct.")
    return df.columns[0]


def parse_datetime_robust(series, filename=""):
    """Tries day-first, then month-first, then per-element mixed inference --
    different input files in this project use different date conventions."""
    try:
        return pd.to_datetime(series, dayfirst=True, errors="raise")
    except (ValueError, TypeError):
        pass
    try:
        return pd.to_datetime(series, dayfirst=False, errors="raise")
    except (ValueError, TypeError):
        pass
    warnings.warn(f"[{filename}] Neither pure day-first nor month-first parsing worked cleanly; "
                   f"used format='mixed' as a last resort. VERIFY this file's dates parsed correctly.")
    return pd.to_datetime(series, format="mixed", dayfirst=True, errors="raise")


def load_wind_generation():
    """Loads all WindTurbine_*.csv files, replicating each site's profile by
    its actual turbine count (see TURBINE_COUNT_PER_SITE), and returns total
    wind generation in MW."""
    wind_files = sorted(glob.glob(WIND_FILE_PATTERN))
    if not wind_files:
        raise FileNotFoundError(f"No wind turbine files found matching {WIND_FILE_PATTERN}")

    aggregated = None
    for path in wind_files:
        df = pd.read_csv(path)
        dt_col = find_datetime_column(df, filename=os.path.basename(path))
        df[dt_col] = parse_datetime_robust(df[dt_col], filename=os.path.basename(path))
        df = df.set_index(dt_col).sort_index()

        if len(df) != EXPECTED_HOURS:
            warnings.warn(f"{os.path.basename(path)} has {len(df)} rows, expected {EXPECTED_HOURS}.")

        if "ActivePower" not in df.columns:
            raise KeyError(f"'ActivePower' column not found in {path}. Columns present: {list(df.columns)}")

        site_key = os.path.splitext(os.path.basename(path))[0]
        n_turbines = TURBINE_COUNT_PER_SITE.get(site_key, 1)

        series = (df["ActivePower"] * n_turbines).rename(os.path.basename(path))
        aggregated = series if aggregated is None else aggregated.add(series, fill_value=0.0)

    aggregated.name = "wind_mw"
    return aggregated


def load_demand():
    """Loads Load_Profile.csv and sums all columns ending in '[MW]'."""
    df = pd.read_csv(LOAD_PROFILE_FILE)
    dt_col = find_datetime_column(df, filename="Load_Profile.csv")
    df[dt_col] = parse_datetime_robust(df[dt_col], filename="Load_Profile.csv")
    df = df.set_index(dt_col).sort_index()

    mw_cols = [c for c in df.columns if str(c).strip().endswith("[MW]")]
    if not mw_cols:
        raise KeyError(f"No columns ending in '[MW]' found in {LOAD_PROFILE_FILE}. "
                        f"Columns present: {list(df.columns)}")

    demand = df[mw_cols].sum(axis=1)
    demand.name = "demand_mw"
    return demand


def load_normalised_profile(path, label):
    """Loads a normalised (0-1) availability profile (wave or tidal)."""
    df = pd.read_csv(path)
    dt_col = find_datetime_column(df, filename=os.path.basename(path))
    df[dt_col] = parse_datetime_robust(df[dt_col], filename=os.path.basename(path))
    df = df.set_index(dt_col).sort_index()

    value_cols = [c for c in df.columns if c != dt_col]
    if not value_cols:
        raise KeyError(f"No value column found in {path} besides the datetime column.")
    series = df[value_cols[0]].astype(float)

    below_zero = (series < 0).sum()
    above_one = (series > 1).sum()
    if below_zero or above_one:
        warnings.warn(f"{label} profile ({path}) had {below_zero} value(s) < 0 and {above_one} value(s) > 1 "
                       f"before clipping.")
    series = series.clip(lower=0.0, upper=1.0)
    series.name = f"{label}_pu"
    return series


def align_all_series(*series_list):
    """Aligns all provided series to their common timestamp intersection and
    confirms no missing values remain."""
    common_index = series_list[0].index
    for s in series_list[1:]:
        common_index = common_index.intersection(s.index)

    aligned = [s.reindex(common_index) for s in series_list]

    n_common = len(common_index)
    print(f"Common aligned timestamps: {n_common}")
    if n_common != EXPECTED_HOURS:
        warnings.warn(f"Aligned series length ({n_common}) does not equal the expected {EXPECTED_HOURS} hours.")

    for s in aligned:
        if s.isna().any():
            raise ValueError(f"Missing values found in '{s.name}' after alignment -- resolve before plotting.")

    return aligned, common_index


# ==============================================================================
# MAIN
# ==============================================================================

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("Loading wind generation...")
    wind_mw = load_wind_generation()

    print("Loading demand...")
    demand_mw = load_demand()

    print("Loading wave profile...")
    wave_pu = load_normalised_profile(WAVE_PROFILE_FILE, "wave")

    print("Loading tidal profile...")
    tidal_pu = load_normalised_profile(TIDAL_PROFILE_FILE, "tidal")

    (wind_mw, demand_mw, wave_pu, tidal_pu), IDX = align_all_series(wind_mw, demand_mw, wave_pu, tidal_pu)

    # Derived series for plotting
    wind_pu = wind_mw / TOTAL_WIND_CAPACITY_MW
    demand_gw = demand_mw / 1000.0

    print(f"\nWind: {wind_mw.sum():,.1f} MWh/year | mean p.u. = {wind_pu.mean():.3f}")
    print(f"Wave: mean p.u. = {wave_pu.mean():.3f}")
    print(f"Tidal: mean p.u. = {tidal_pu.mean():.3f}")
    print(f"Demand: {demand_mw.sum():,.1f} MWh/year | mean = {demand_gw.mean():.3f} GW")

    # ── 4-panel resource overview figure ──────────────────────────────────────
    try:
        fig, axes = plt.subplots(4, 1, figsize=(12, 9), sharex=True,
                                  gridspec_kw={"hspace": 0.45})

        panels = [
            (axes[0], wave_pu, C_WAVE, "Wave (pu)", "Wave Resource — Billia Croo (CorPower 2019)", (0, 1.05)),
            (axes[1], tidal_pu, C_TIDAL, "Tidal (pu)", "Tidal Resource — Westray-South (2019)", (0, 1.05)),
            (axes[2], wind_pu, C_WIND, "Wind (pu)", "Combined Wind — All Orkney Farms", (0, 1.05)),
            (axes[3], demand_gw, C_DEMAND, "Demand (GW)", "Orkney Total Demand", None),
        ]
        for ax, series, col, ylabel, title, ylim in panels:
            ax.fill_between(IDX, series.values, alpha=0.60, color=col)
            ax.plot(IDX, series.values, color=col, linewidth=0.3, alpha=0.4)
            ax.set_ylabel(ylabel, fontsize=12)
            ax.set_title(title, fontsize=13, pad=3)
            if ylim:
                ax.set_ylim(*ylim)

        axes[3].xaxis.set_major_locator(mdates.MonthLocator())
        axes[3].xaxis.set_major_formatter(mdates.DateFormatter("%b"))
        axes[3].set_xlabel("2019", fontsize=14)

        fig.suptitle("Orkney 2019 — Energy Resource Overview", fontsize=16, fontweight="bold")

        path = os.path.join(OUTPUT_DIR, "Figure1_Resource_Overview.png")
        fig.savefig(path, dpi=300, bbox_inches="tight")
        plt.show()
        print(f"\nSaved: {path}")
    except Exception as e:
        print(f"ERROR — Figure 1 failed: {e}")
        plt.close("all")


if __name__ == "__main__":
    main()