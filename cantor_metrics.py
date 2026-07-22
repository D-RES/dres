"""
cantor_complementarity.py
──────────────────────────
Computes Cantor, Ochoa and Mesa (2022) total variation-based
complementarity indices:

  Phi   — Total Variation Complementarity Index  (Eq. 5, primary metric)
  Phi'  — Variance Complementarity Index         (Eq. 8-10)
  Phi_s — Standard Deviation Complementarity Index (Eq. 11)

For all pairwise and three-resource combinations of wind, wave, tidal.

Reference:
  Cantor, D., Ochoa, A. and Mesa, O. (2022) 'Total Variation-Based
  Metrics for Assessing Complementarity in Energy Resources Time Series',
  Sustainability, 14(14), p. 8514.
  https://doi.org/10.3390/su14148514
"""

import pandas as pd
import numpy as np

# ── Load combined dataset ─────────────────────────────────────────
data  = pd.read_csv("DATA/outputs/complementarity_input_data.csv",
                    index_col='time', parse_dates=True)

wind  = data['wind_pu'].values
wave  = data['wave_pu'].values
tidal = data['tidal_pu'].values

# ── Total Variation (Cantor et al. Eq. 1, 4) ─────────────────────
def total_variation(series_list):
    """
    TV(f) = sum_k |f(t_{k+1}) - f(t_k)|
    Accepts a list of arrays — sums them first then computes TV.
    """
    f = np.sum(series_list, axis=0)
    return np.sum(np.abs(np.diff(f)))

# ── Phi — Total Variation Complementarity Index (Cantor et al. Eq. 5) ─
def phi_total_variation(series_list):
    """
    Phi(f1,...,fn) = 1 - TV(f1+f2+...+fn) / (TV(f1)+TV(f2)+...+TV(fn))

    Range: 0 (no complementarity) to 1 (perfect complementarity).
    Primary recommended metric — explicitly captures autocorrelation
    structure unlike Phi' and Phi_s.
    """
    tv_sum            = total_variation(series_list)
    tv_individual_sum = sum(total_variation([s]) for s in series_list)
    return 1 - (tv_sum / tv_individual_sum)

# ── Phi' — Variance Complementarity Index (Cantor et al. Eq. 8-10) ──
def phi_variance(series_list):
    """
    Phi_v(f1,f2) = 1 - Var[f1+f2] / (Var(f1)+Var(f2))
    Phi'         = (Phi_v + 1) / 2   [rescaled to (0,1)]

    Note: systematically overestimates complementarity relative to Phi
    (Cantor et al., 2022, Section 4) — retained for reference only.
    """
    f                  = np.sum(series_list, axis=0)
    var_sum            = np.var(f, ddof=1)
    var_individual_sum = sum(np.var(s, ddof=1) for s in series_list)
    phi_v              = 1 - (var_sum / var_individual_sum)
    phi_prime          = (phi_v + 1) / 2
    return phi_prime

# ── Phi_s — Standard Deviation Complementarity Index (Cantor et al. Eq. 11) ─
def phi_std(series_list):
    """
    Phi_s(f1,f2) = 1 - std(f1+f2) / (std(f1)+std(f2))

    Range: naturally within (0,1) without rescaling.
    Also overestimates relative to Phi — retained for reference only.
    """
    f                  = np.sum(series_list, axis=0)
    std_sum            = np.std(f, ddof=1)
    std_individual_sum = sum(np.std(s, ddof=1) for s in series_list)
    return 1 - (std_sum / std_individual_sum)

# ── Compute for all resource combinations ─────────────────────────
combinations = {
    "Wind-Wave":       [wind, wave],
    "Wind-Tidal":      [wind, tidal],
    "Wave-Tidal":      [wave, tidal],
    "Wind-Wave-Tidal": [wind, wave, tidal],
}

results = []
for name, series_list in combinations.items():
    phi   = phi_total_variation(series_list)
    phi_p = phi_variance(series_list)
    phi_s = phi_std(series_list)
    results.append({
        "Resource Mix":          name,
        "Phi (Total Variation)": round(phi,   4),
        "Phi' (Variance)":       round(phi_p, 4),
        "Phi_s (Std Dev)":       round(phi_s, 4),
    })

results_df = pd.DataFrame(results)
print("=== CANTOR ET AL. COMPLEMENTARITY INDICES — ORKNEY 2019 ===\n")
print(results_df.to_string(index=False))

# ── Save ──────────────────────────────────────────────────────────
results_df.to_csv("DATA/outputs/cantor_complementarity_results.csv", index=False)
print("\nSaved: DATA/outputs/cantor_complementarity_results.csv")

# ── Sanity check vs Said et al. (2023) Ireland results ────────────
print("\n--- Sanity check (Said et al. 2023, Table II, Ireland) ---")
print("Reported: Wave-wind=0.1055, Wind-tidal=0.1930, Wave-wind-tidal=0.2647")
print("Pattern expected: three-resource Phi > any pairwise Phi")

ww    = results_df.loc[results_df['Resource Mix']=='Wind-Wave',  'Phi (Total Variation)'].values[0]
wt    = results_df.loc[results_df['Resource Mix']=='Wind-Tidal', 'Phi (Total Variation)'].values[0]
vt    = results_df.loc[results_df['Resource Mix']=='Wave-Tidal', 'Phi (Total Variation)'].values[0]
three = results_df.loc[results_df['Resource Mix']=='Wind-Wave-Tidal', 'Phi (Total Variation)'].values[0]

print(f"Your data: Wind-Wave={ww}, Wind-Tidal={wt}, Wave-Tidal={vt}, Three-way={three}")
print(f"Three-way > all pairwise? {three > max(ww, wt, vt)}")

# ── Note on metric interpretation ────────────────────────────────
print("""
--- Interpretation note ---
Phi  (primary):  directly captures temporal autocorrelation structure.
                 Recommended by Cantor et al. (2022) as the preferred metric.
Phi' (variance): simplifies to a scaled Pearson correlation.
                 Systematically overestimates complementarity.
Phi_s (std dev): similar overestimation issue to Phi'.
                 Retained for robustness comparison only.

All values range from 0 (no complementarity) to 1 (perfect complementarity).
Higher = more complementary = combined output is more regular than individual outputs.
""")