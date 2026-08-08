"""
complementarity_analysis_combined.py

Single, self-contained complementarity analysis script for the complete,
aligned 2019 hourly dataset (8,760 observations).

All metrics -- capacity factor, Resource Availability (RA), Resource
Persistence (RP), Resource Versatility (RV), Pearson correlation (CC), and
the total-variation complementarity index (Phi) -- are calculated over the
FULL 2019 CALENDAR YEAR ONLY. No seasonal analysis is undertaken anywhere
in this script.

Sensitivity analysis is applied ONLY to the RA, RP and RV parameter
choices (availability threshold and persistence window), using the same
complete annual dataset and the same calculation approach as the base
case -- the sensitivity analysis varies the assumptions, not the temporal
scope. Annual Phi and Pearson correlation are retained exactly as
originally calculated (threshold and persistence window do not apply to
either), and are not varied or recalculated under alternative parameters.

Computes:
  - Capacity factor, Resource Availability (RA), Resource Persistence (RP),
    Resource Versatility (RV) -- Pennock et al. (2022), annual only
  - Pearson correlation (CC), annual only
  - Total-variation complementarity index, Phi -- Cantor, Ochoa and Mesa
    (2022), Sustainability, 14(14), 8514. https://doi.org/10.3390/su14148514,
    annual only, not varied by threshold or persistence window
  - Analytical sensitivity testing of RA, RP and RV across thresholds
    (0.10/0.20/0.30) and persistence windows (1/3/6h), applied to the same
    complete 2019 hourly dataset used for the base case.

Does NOT rerun or introduce PyPSA -- operates only on the existing aligned,
normalised wind/wave/tidal profiles and demand loaded from
DATA/outputs/complementarity_input_data.csv.

The code calculates only; no automated "robust"/"holds"/interpretive
language is produced anywhere -- interpretation is written separately in
the dissertation. See sensitivity_summary.csv and base_case_validation.csv
for factual, calculated outputs only.
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import os

OUTPUT_DIR = "DATA/outputs"
FIGURES_DIR = f"{OUTPUT_DIR}/figures"
os.makedirs(FIGURES_DIR, exist_ok=True)

COLOURS = {"Wind": "#7fa8d9", "Wave": "#e8a33d", "Tidal": "#4a7c3f"}


# ══════════════════════════════════════════════════════════════════════════
# DATA LOADING + VALIDATION CHECKS -- UNCHANGED
# ══════════════════════════════════════════════════════════════════════════

data = pd.read_csv("DATA/outputs/complementarity_input_data.csv", index_col='time', parse_dates=True)

if len(data) != 8760:
    raise ValueError(f"Expected exactly 8760 observations, found {len(data)}. Investigate before proceeding.")

if not data.index.is_monotonic_increasing:
    raise ValueError("Datetime index is not monotonic increasing. Investigate row ordering before proceeding.")

if not data.index.is_unique:
    dupes = data.index[data.index.duplicated()].tolist()
    raise ValueError(f"Duplicate timestamps found: {dupes[:10]}{'...' if len(dupes) > 10 else ''}. Investigate before proceeding.")

if data[['wind_pu', 'wave_pu', 'tidal_pu', 'demand_mw']].isna().any().any():
    na_summary = data[['wind_pu', 'wave_pu', 'tidal_pu', 'demand_mw']].isna().sum()
    raise ValueError(f"Missing values found:\n{na_summary}\nInvestigate before proceeding.")

expected_range = pd.date_range(start=data.index[0], periods=8760, freq="h")
if not data.index.equals(expected_range):
    mismatches = data.index.symmetric_difference(expected_range)
    raise ValueError(f"Index is not perfectly hourly-continuous from {data.index[0]}. "
                      f"{len(mismatches)} mismatched timestamp(s), e.g. {list(mismatches[:5])}. Investigate before proceeding.")

expected_start = pd.Timestamp("2019-01-01 00:00:00")
expected_end = pd.Timestamp("2019-12-31 23:00:00")
if data.index[0] != expected_start or data.index[-1] != expected_end:
    raise ValueError(
        f"Expected the complete 2019 calendar year from {expected_start} "
        f"to {expected_end}, but found {data.index[0]} to {data.index[-1]}."
    )

FLOAT_TOL = 1e-9
for col in ['wind_pu', 'wave_pu', 'tidal_pu']:
    below = data[col] < (0 - FLOAT_TOL)
    above = data[col] > (1 + FLOAT_TOL)
    if below.any() or above.any():
        raise ValueError(f"Column '{col}' has {below.sum()} value(s) below 0 and {above.sum()} value(s) above 1 "
                          f"(beyond float tolerance {FLOAT_TOL}). Investigate before proceeding.")

print("=== DATA VALIDATION: ALL CHECKS PASSED ===")
print(f"  Observations: {len(data)} | Index monotonic: {data.index.is_monotonic_increasing} | "
      f"Unique: {data.index.is_unique} | Hourly-continuous: True | 2019 calendar year confirmed: True | "
      f"No missing values: True | wind/wave/tidal within [0,1]: True\n")

wind = data['wind_pu'].values
wave = data['wave_pu'].values
tidal = data['tidal_pu'].values
demand = data['demand_mw'].values

resources = {"Wind": wind, "Wave": wave, "Tidal": tidal}


# ══════════════════════════════════════════════════════════════════════════
# PENNOCK ET AL. (2022): RA / RP / RV / CC FORMULAS -- UNCHANGED
# ══════════════════════════════════════════════════════════════════════════

def resource_availability(x, threshold=0.2):
    """Proportion of hours where output is STRICTLY greater than threshold
    (Pennock et al., Eq. 2). Output == threshold does NOT count."""
    ra_t = (x > threshold).astype(int)
    return ra_t.mean()


def resource_persistence(x, threshold=0.2, tau=3):
    """Proportion of eligible tau-hour windows where output remains
    STRICTLY above threshold for every hour in the window (Pennock et al.,
    Eq. 3/4). Denominator is the correct N - tau + 1 eligible-window count."""
    if tau < 1:
        raise ValueError("Persistence window tau must be at least 1.")
    if tau > len(x):
        raise ValueError(f"Persistence window tau={tau} exceeds series length {len(x)}.")
    ra_t = (x > threshold).astype(int)
    T = len(ra_t)
    rp_count = 0
    n_windows = T - tau + 1
    for j in range(n_windows):
        if ra_t[j:j + tau].all():
            rp_count += 1
    return rp_count / n_windows, rp_count, n_windows


def resource_versatility(x_a, x_b, x_c, threshold=0.2):
    """Proportion of hours where resource A is STRICTLY available while
    BOTH B and C are at or below threshold (Pennock et al., Eq. 5/6)."""
    ra_a = (x_a > threshold).astype(int)
    ra_b = (x_b > threshold).astype(int)
    ra_c = (x_c > threshold).astype(int)
    rv_t = ((ra_a == 1) & (ra_b == 0) & (ra_c == 0)).astype(int)
    return rv_t.mean()


def correlation_coefficient(x, y):
    return np.corrcoef(x, y)[0, 1]


# ══════════════════════════════════════════════════════════════════════════
# CANTOR, OCHOA AND MESA (2022): TOTAL-VARIATION COMPLEMENTARITY, Phi
# UNCHANGED. Annual only -- Phi does not take a threshold or persistence
# window parameter, so it is not part of the sensitivity analysis.
# ══════════════════════════════════════════════════════════════════════════

def total_variation(series_list):
    """
    TV(f) = sum_k |f(t_{k+1}) - f(t_k)|
    Accepts a list of arrays -- sums them first (NOT averaged) then
    computes TV of the resulting combined series.
    """
    f = np.sum(series_list, axis=0)
    return np.sum(np.abs(np.diff(f)))


def phi_total_variation(series_list):
    """
    Phi(f1,...,fn) = 1 - TV(f1+f2+...+fn) / (TV(f1)+TV(f2)+...+TV(fn))
    Range: 0 (no complementarity) to 1 (perfect complementarity).
    Returns np.nan if the sum of individual total variations is zero
    (zero-denominator protection).
    """
    tv_sum = total_variation(series_list)
    tv_individual_sum = sum(total_variation([s]) for s in series_list)
    if np.isclose(tv_individual_sum, 0.0):
        return np.nan
    return 1 - (tv_sum / tv_individual_sum)


# ── Base-case RA/RP/RV/CC computation, threshold=0.20, tau=3h -- full precision ──
print("=== RESOURCE AVAILABILITY (RA) & PERSISTENCE (RP) -- threshold=0.2, tau=3hrs ===\n")
ra_rp_results = []
for name, series in resources.items():
    cf = series.mean()
    ra = resource_availability(series, threshold=0.2)
    rp, _, _ = resource_persistence(series, threshold=0.2, tau=3)
    ra_rp_results.append({"Resource": name, "Capacity Factor": cf, "RA(0.2)": ra, "RP(0.2,3)": rp})
ra_rp_df = pd.DataFrame(ra_rp_results)
print(ra_rp_df.to_string(index=False, formatters={
    "Capacity Factor": "{:.3f}".format, "RA(0.2)": "{:.3f}".format, "RP(0.2,3)": "{:.3f}".format}))

print("\n\n=== RESOURCE VERSATILITY (RV) -- threshold=0.2 ===\n")
rv_wind = resource_versatility(wind, wave, tidal, threshold=0.2)
rv_wave = resource_versatility(wave, wind, tidal, threshold=0.2)
rv_tidal = resource_versatility(tidal, wind, wave, threshold=0.2)
rv_df = pd.DataFrame([
    {"Resource": "Wind", "RV(0.2)": rv_wind},
    {"Resource": "Wave", "RV(0.2)": rv_wave},
    {"Resource": "Tidal", "RV(0.2)": rv_tidal},
])
print(rv_df.to_string(index=False, formatters={"RV(0.2)": "{:.3f}".format}))

print("\n\n=== CORRELATION COEFFICIENT (CC) -- Pairwise & vs Demand ===\n")
cc_df = pd.DataFrame([
    {"Pair": "Wind-Wave", "CC": correlation_coefficient(wind, wave)},
    {"Pair": "Wind-Tidal", "CC": correlation_coefficient(wind, tidal)},
    {"Pair": "Wave-Tidal", "CC": correlation_coefficient(wave, tidal)},
    {"Pair": "Wind-Demand", "CC": correlation_coefficient(wind, demand)},
    {"Pair": "Wave-Demand", "CC": correlation_coefficient(wave, demand)},
    {"Pair": "Tidal-Demand", "CC": correlation_coefficient(tidal, demand)},
])
print(cc_df.to_string(index=False, formatters={"CC": "{:.3f}".format}))

ra_rp_df.to_csv(f"{OUTPUT_DIR}/pennock_RA_RP_results.csv", index=False)
rv_df.to_csv(f"{OUTPUT_DIR}/pennock_RV_results.csv", index=False)
cc_df.to_csv(f"{OUTPUT_DIR}/pennock_CC_results.csv", index=False)
print(f"\n\nSaved: pennock_RA_RP_results.csv, pennock_RV_results.csv, pennock_CC_results.csv (full precision)")


# ── Annual total-variation complementarity -- UNCHANGED, not varied by threshold/window ──
tv_pairs = {
    "Wind-Wave": [wind, wave], "Wind-Tidal": [wind, tidal],
    "Wave-Tidal": [wave, tidal], "Wind-Wave-Tidal": [wind, wave, tidal],
}

print("\n\n=== TOTAL-VARIATION COMPLEMENTARITY -- Phi (Cantor et al., 2022), ANNUAL ===\n")
tv_annual_results = []
for label, series_list in tv_pairs.items():
    phi = phi_total_variation(series_list)
    tv_annual_results.append({"resource_combination": label, "total_variation_complementarity": phi})
    print(f"  {label}: Phi = {phi:.4f}")

tv_annual_df = pd.DataFrame(tv_annual_results)
tv_annual_df.to_csv(f"{OUTPUT_DIR}/annual_total_variation_results.csv", index=False)

top_annual_phi = tv_annual_df.loc[tv_annual_df["total_variation_complementarity"].idxmax()]
print(f"\nHighest annual Phi: {top_annual_phi['resource_combination']} "
      f"({top_annual_phi['total_variation_complementarity']:.4f})")
print("Saved: annual_total_variation_results.csv")


# ══════════════════════════════════════════════════════════════════════════
# BASE-CASE VALIDATION TABLE -- UNCHANGED
# ══════════════════════════════════════════════════════════════════════════

TOLERANCE = 0.005

VERIFIED_BASE_CASE = {
    "Wind": {"CF": 0.462, "RA": 0.679, "RP": 0.634, "RV": 0.102},
    "Wave": {"CF": 0.413, "RA": 0.631, "RP": 0.615, "RV": 0.082},
    "Tidal": {"CF": 0.393, "RA": 0.584, "RP": 0.276, "RV": 0.074},
}
VERIFIED_ANNUAL_PHI = {
    "Wind-Wave": 0.1257, "Wind-Tidal": 0.1236, "Wave-Tidal": 0.0546, "Wind-Wave-Tidal": 0.1634,
}

rv_lookup = {"Wind": rv_wind, "Wave": rv_wave, "Tidal": rv_tidal}
calc_lookup = {}
for name, series in resources.items():
    rp, _, _ = resource_persistence(series, threshold=0.2, tau=3)
    calc_lookup[name] = {"CF": series.mean(), "RA": resource_availability(series, threshold=0.2),
                          "RP": rp, "RV": rv_lookup[name]}

validation_rows = []
for name in ["Wind", "Wave", "Tidal"]:
    for metric in ["CF", "RA", "RP", "RV"]:
        verified = VERIFIED_BASE_CASE[name][metric]
        calculated = calc_lookup[name][metric]
        diff = abs(calculated - verified)
        validation_rows.append({
            "category": "resource_metric", "resource_or_combination": name, "metric": metric,
            "verified_value": verified, "calculated_value": calculated,
            "absolute_difference": diff, "tolerance": TOLERANCE,
            "status": "PASS" if diff <= TOLERANCE else "FAIL",
        })

for combo, verified in VERIFIED_ANNUAL_PHI.items():
    calculated = tv_annual_df.loc[tv_annual_df["resource_combination"] == combo, "total_variation_complementarity"].values[0]
    diff = abs(calculated - verified)
    validation_rows.append({
        "category": "annual_phi", "resource_or_combination": combo, "metric": "Phi",
        "verified_value": verified, "calculated_value": calculated,
        "absolute_difference": diff, "tolerance": TOLERANCE,
        "status": "PASS" if diff <= TOLERANCE else "FAIL",
    })

base_case_validation_df = pd.DataFrame(validation_rows)
base_case_validation_df.to_csv(f"{OUTPUT_DIR}/base_case_validation.csv", index=False)

n_pass = (base_case_validation_df["status"] == "PASS").sum()
n_total = len(base_case_validation_df)
print("\n\n" + "=" * 100)
print(f"BASE-CASE VALIDATION: {n_pass}/{n_total} checks PASS (tolerance={TOLERANCE})")
print("=" * 100)
print(base_case_validation_df.to_string(index=False, formatters={
    "verified_value": "{:.4f}".format, "calculated_value": "{:.4f}".format, "absolute_difference": "{:.4f}".format}))
if n_pass < n_total:
    print(f"\n*** {n_total - n_pass} CHECK(S) FAILED. Values were NOT overwritten or forced to match. ***")
print(f"\nSaved: base_case_validation.csv")


# ══════════════════════════════════════════════════════════════════════════
# ANNUAL SENSITIVITY ANALYSIS -- thresholds and persistence windows only,
# same complete 2019 hourly dataset used throughout. NO seasonal analysis.
# ══════════════════════════════════════════════════════════════════════════

THRESHOLDS = [0.10, 0.20, 0.30]
PERSISTENCE_WINDOWS = [1, 3, 6]


def compute_ra_rv_sensitivity(series_dict):
    rows = []
    names = list(series_dict.keys())
    for threshold in THRESHOLDS:
        for name in names:
            x = series_dict[name]
            others = [series_dict[n] for n in names if n != name]
            ra = resource_availability(x, threshold=threshold)
            rv = resource_versatility(x, others[0], others[1], threshold=threshold)
            rows.append({"resource": name, "threshold": threshold, "resource_availability": ra, "resource_versatility": rv})
    return rows


def compute_rp_sensitivity_annual(series_dict):
    rows = []
    for name, x in series_dict.items():
        for threshold in THRESHOLDS:
            for window in PERSISTENCE_WINDOWS:
                rp, successful, eligible = resource_persistence(x, threshold=threshold, tau=window)
                rows.append({"resource": name, "threshold": threshold, "persistence_window_hours": window,
                             "resource_persistence": rp, "eligible_windows": eligible, "successful_windows": successful})
    return rows


print("\n\n=== ANNUAL RA/RV SENSITIVITY (thresholds 0.10, 0.20, 0.30) ===")
annual_ra_rv_rows = compute_ra_rv_sensitivity(resources)
annual_ra_rv_df = pd.DataFrame(annual_ra_rv_rows)
print(annual_ra_rv_df.to_string(index=False, formatters={
    "resource_availability": "{:.4f}".format, "resource_versatility": "{:.4f}".format}))

print("\n\n=== ANNUAL RP SENSITIVITY (3 thresholds x 3 windows) ===")
annual_rp_rows = compute_rp_sensitivity_annual(resources)
annual_rp_df = pd.DataFrame(annual_rp_rows)
print(annual_rp_df.to_string(index=False, formatters={"resource_persistence": "{:.4f}".format}))

annual_ra_rv_df.to_csv(f"{OUTPUT_DIR}/annual_ra_rv_sensitivity.csv", index=False)
annual_rp_df.to_csv(f"{OUTPUT_DIR}/annual_rp_sensitivity.csv", index=False)
print(f"\n\nSaved: annual_ra_rv_sensitivity.csv, annual_rp_sensitivity.csv")


# ══════════════════════════════════════════════════════════════════════════
# FIGURES -- annual sensitivity only, unchanged style/colours
# ══════════════════════════════════════════════════════════════════════════

RESOURCE_ORDER = ["Wind", "Wave", "Tidal"]

fig, ax = plt.subplots(figsize=(7, 4.5))
width = 0.25
x = np.arange(len(THRESHOLDS))
for i, name in enumerate(RESOURCE_ORDER):
    vals = annual_ra_rv_df[annual_ra_rv_df["resource"] == name].sort_values("threshold")["resource_availability"]
    ax.bar(x + i * width, vals, width, label=name, color=COLOURS[name])
ax.set_xticks(x + width); ax.set_xticklabels([f"{t:.2f}" for t in THRESHOLDS])
ax.set_xlabel("Availability threshold"); ax.set_ylabel("Resource availability, RA")
ax.set_title("Annual RA sensitivity by resource and threshold"); ax.legend()
fig.tight_layout(); fig.savefig(f"{FIGURES_DIR}/ra_sensitivity_annual.png", dpi=300); plt.close(fig)

fig, ax = plt.subplots(figsize=(7, 4.5))
for i, name in enumerate(RESOURCE_ORDER):
    vals = annual_ra_rv_df[annual_ra_rv_df["resource"] == name].sort_values("threshold")["resource_versatility"]
    ax.bar(x + i * width, vals, width, label=name, color=COLOURS[name])
ax.set_xticks(x + width); ax.set_xticklabels([f"{t:.2f}" for t in THRESHOLDS])
ax.set_xlabel("Availability threshold"); ax.set_ylabel("Resource versatility, RV")
ax.set_title("Annual RV sensitivity by resource and threshold"); ax.legend()
fig.tight_layout(); fig.savefig(f"{FIGURES_DIR}/rv_sensitivity_annual.png", dpi=300); plt.close(fig)

fig, axes = plt.subplots(1, 3, figsize=(13, 4.2), sharey=True)
for ax, name in zip(axes, RESOURCE_ORDER):
    sub = annual_rp_df[annual_rp_df["resource"] == name]
    for threshold in THRESHOLDS:
        vals = sub[sub["threshold"] == threshold].sort_values("persistence_window_hours")
        ax.plot(vals["persistence_window_hours"], vals["resource_persistence"], marker="o",
                label=f"threshold={threshold:.2f}", color=COLOURS[name],
                alpha=1.0 if threshold == 0.20 else 0.5, linestyle="-" if threshold == 0.20 else "--")
    ax.set_title(name); ax.set_xlabel("Persistence window (hours)"); ax.set_xticks(PERSISTENCE_WINDOWS)
axes[0].set_ylabel("Resource persistence, RP"); axes[-1].legend(fontsize=8)
fig.suptitle("Resource persistence sensitivity")
fig.tight_layout(); fig.savefig(f"{FIGURES_DIR}/rp_sensitivity.png", dpi=300); plt.close(fig)

print(f"\nSaved 3 figures to {FIGURES_DIR}/: ra_sensitivity_annual.png, rv_sensitivity_annual.png, rp_sensitivity.png")


# ══════════════════════════════════════════════════════════════════════════
# FACTUAL SENSITIVITY SUMMARY -- annual only, no interpretive/robustness language
# ══════════════════════════════════════════════════════════════════════════

summary_rows = []

# RA ranking at each threshold
for threshold in THRESHOLDS:
    sub = annual_ra_rv_df[annual_ra_rv_df["threshold"] == threshold].sort_values("resource_availability", ascending=False)
    ranking = " > ".join(sub["resource"].tolist())
    summary_rows.append({"category": "RA ranking", "detail": f"threshold={threshold:.2f}", "value": ranking})

# RV values and ranking at each threshold
for threshold in THRESHOLDS:
    sub = annual_ra_rv_df[annual_ra_rv_df["threshold"] == threshold].sort_values("resource_versatility", ascending=False)
    ranking = " > ".join(sub["resource"].tolist())
    values = ", ".join(f"{row.resource}={row.resource_versatility:.6f}" for row in sub.itertuples())
    summary_rows.append({"category": "RV ranking", "detail": f"threshold={threshold:.2f}", "value": ranking})
    summary_rows.append({"category": "RV values", "detail": f"threshold={threshold:.2f}", "value": values})

# RP values and ranking for every threshold-window combination
for threshold in THRESHOLDS:
    for window in PERSISTENCE_WINDOWS:
        sub = annual_rp_df[(annual_rp_df.threshold == threshold) & (annual_rp_df.persistence_window_hours == window)]
        sub_ranked = sub.sort_values("resource_persistence", ascending=False)
        ranking = " > ".join(sub_ranked["resource"].tolist())
        values = ", ".join(f"{row.resource}={row.resource_persistence:.6f}" for row in sub_ranked.itertuples())
        summary_rows.append({"category": "RP ranking", "detail": f"threshold={threshold:.2f}, window={window}h", "value": ranking})
        summary_rows.append({"category": "RP values", "detail": f"threshold={threshold:.2f}, window={window}h", "value": values})

# Highest annual Phi combination
summary_rows.append({
    "category": "Highest annual Phi combination", "detail": "-",
    "value": f"{top_annual_phi['resource_combination']} ({top_annual_phi['total_variation_complementarity']:.4f})",
})

sensitivity_summary_df = pd.DataFrame(summary_rows)
sensitivity_summary_df.to_csv(f"{OUTPUT_DIR}/sensitivity_summary.csv", index=False)

print("\n\n" + "=" * 100)
print("SENSITIVITY SUMMARY (factual outputs only, annual)")
print("=" * 100)
print(sensitivity_summary_df.to_string(index=False))

print(f"\n\nAll output files saved to {OUTPUT_DIR}/ and {FIGURES_DIR}/.")