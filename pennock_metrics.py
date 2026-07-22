import pandas as pd
import numpy as np

# ── Load combined dataset ───────────────────────────────────────────────────
data = pd.read_csv("DATA/outputs/complementarity_input_data.csv", index_col='time', parse_dates=True)

wind  = data['wind_pu'].values
wave  = data['wave_pu'].values
tidal = data['tidal_pu'].values
demand = data['demand_mw'].values

resources = {"Wind": wind, "Wave": wave, "Tidal": tidal}

# ═══════════════════════════════════════════════════════════════════════
# RA — Resource Availability (Pennock et al. Eq. 2)
# Proportion of time resource exceeds threshold x_tilde
# ═══════════════════════════════════════════════════════════════════════
def resource_availability(x, threshold=0.2):
    ra_t = (x > threshold).astype(int)
    return ra_t.mean()

# ═══════════════════════════════════════════════════════════════════════
# RP — Resource Persistence (Pennock et al. Eq. 3/4)
# Proportion of sub-windows of length tau where resource stays above
# threshold for ALL tau consecutive hours
# ═══════════════════════════════════════════════════════════════════════
def resource_persistence(x, threshold=0.2, tau=3):
    ra_t = (x > threshold).astype(int)
    T = len(ra_t)
    rp_count = 0
    n_windows = T - tau + 1
    for j in range(n_windows):
        if ra_t[j:j+tau].all():
            rp_count += 1
    return rp_count / n_windows

# ═══════════════════════════════════════════════════════════════════════
# RV — Resource Versatility (Pennock et al. Eq. 5/6)
# Proportion of time resource A is available (>threshold) while
# resources B and C are NOT available (<=threshold)
# ═══════════════════════════════════════════════════════════════════════
def resource_versatility(x_a, x_b, x_c, threshold=0.2):
    ra_a = (x_a > threshold).astype(int)
    ra_b = (x_b > threshold).astype(int)
    ra_c = (x_c > threshold).astype(int)
    rv_t = ((ra_a == 1) & (ra_b == 0) & (ra_c == 0)).astype(int)
    return rv_t.mean()

# ═══════════════════════════════════════════════════════════════════════
# CC — Correlation Coefficient (Pennock et al. Eq. 1, standard Pearson)
# ═══════════════════════════════════════════════════════════════════════
def correlation_coefficient(x, y):
    return np.corrcoef(x, y)[0, 1]

# ── Compute RA, RP for each resource individually ───────────────────────
print("=== RESOURCE AVAILABILITY (RA) & PERSISTENCE (RP) — threshold=0.2, tau=3hrs ===\n")
ra_rp_results = []
for name, series in resources.items():
    cf = series.mean()
    ra = resource_availability(series, threshold=0.2)
    rp = resource_persistence(series, threshold=0.2, tau=3)
    ra_rp_results.append({
        "Resource": name,
        "Capacity Factor": round(cf, 3),
        "RA(0.2)": round(ra, 3),
        "RP(0.2,3)": round(rp, 3),
    })
ra_rp_df = pd.DataFrame(ra_rp_results)
print(ra_rp_df.to_string(index=False))

# ── Compute RV for each resource relative to the other two ─────────────
print("\n\n=== RESOURCE VERSATILITY (RV) — threshold=0.2 ===\n")
rv_results = []
rv_wind  = resource_versatility(wind, wave, tidal, threshold=0.2)
rv_wave  = resource_versatility(wave, wind, tidal, threshold=0.2)
rv_tidal = resource_versatility(tidal, wind, wave, threshold=0.2)
rv_results = [
    {"Resource": "Wind",  "RV(0.2) — available when others aren't": round(rv_wind, 3)},
    {"Resource": "Wave",  "RV(0.2) — available when others aren't": round(rv_wave, 3)},
    {"Resource": "Tidal", "RV(0.2) — available when others aren't": round(rv_tidal, 3)},
]
rv_df = pd.DataFrame(rv_results)
print(rv_df.to_string(index=False))

# ── Compute CC pairwise (resource-resource) and resource-demand ────────
print("\n\n=== CORRELATION COEFFICIENT (CC) — Pairwise & vs Demand ===\n")
cc_results = [
    {"Pair": "Wind-Wave",       "CC": round(correlation_coefficient(wind, wave), 3)},
    {"Pair": "Wind-Tidal",      "CC": round(correlation_coefficient(wind, tidal), 3)},
    {"Pair": "Wave-Tidal",      "CC": round(correlation_coefficient(wave, tidal), 3)},
    {"Pair": "Wind-Demand",     "CC": round(correlation_coefficient(wind, demand), 3)},
    {"Pair": "Wave-Demand",     "CC": round(correlation_coefficient(wave, demand), 3)},
    {"Pair": "Tidal-Demand",    "CC": round(correlation_coefficient(tidal, demand), 3)},
]
cc_df = pd.DataFrame(cc_results)
print(cc_df.to_string(index=False))

# ── Save all results ─────────────────────────────────────────────────────
ra_rp_df.to_csv("DATA/outputs/pennock_RA_RP_results.csv", index=False)
rv_df.to_csv("DATA/outputs/pennock_RV_results.csv", index=False)
cc_df.to_csv("DATA/outputs/pennock_CC_results.csv", index=False)
print("\n\nSaved: pennock_RA_RP_results.csv, pennock_RV_results.csv, pennock_CC_results.csv")

# ── Sanity check vs Pennock et al. (Orkney & North region, their Table 8) ──
print("\n--- Sanity check (Pennock et al. 2022, Table 8, Orkney & North) ---")
print("Reported: Onshore wind RA(0.2)=0.74, Wave RA(0.2)=0.69, Tidal stream RA(0.2)=0.63")
print("Reported: Onshore wind RP(0.2,3)=0.71, Wave RP(0.2,3)=0.67, Tidal RP(0.2,3)=0.31")
print("Reported CC with load: Wind=0.06, Wave=0.27, Tidal=-0.01")
print(f"\nYour data CC with demand: Wind={cc_df.loc[cc_df['Pair']=='Wind-Demand','CC'].values[0]}, "
      f"Wave={cc_df.loc[cc_df['Pair']=='Wave-Demand','CC'].values[0]}, "
      f"Tidal={cc_df.loc[cc_df['Pair']=='Tidal-Demand','CC'].values[0]}")