"""
run_full_year_ac_screening.py

Full-year nonlinear AC power-flow screening across all 15 scenarios,
extending the 5-hour critical-hour screening in validate_scenario.py to
every hour of the year.

Key efficiency choice vs. the critical-hour version: the network is loaded
ONCE per scenario, and pf() is called ONCE across all 8,760 snapshots
(PyPSA loops internally, in C-accelerated Newton-Raphson per snapshot,
without the Python-level overhead of re-importing from disk each time).

USAGE:
    python run_full_year_ac_screening.py
        -> runs all 15 scenarios found in FILES, saves per-hour CSVs and
           a consolidated summary CSV to DATA/outputs/full_year_ac_screening/

    For a single-scenario pilot run (recommended before the full batch):
        from run_full_year_ac_screening import screen_scenario_full_year
        summary, per_hour = screen_scenario_full_year(
            "R11", "DATA/outputs/wave_storage_scaling_v1/R11_wave30MW_batt4x.nc"
        )
"""

import os
import time
import numpy as np
import pandas as pd
import pypsa

FILES = {
    "R01": ("DATA/outputs/wave_storage_core_harmonised_v1", "R01_wave0MW_batt2x.nc"),
    "R02": ("DATA/outputs/wave_storage_core_harmonised_v1", "R02_wave5MW_batt2x.nc"),
    "R06": ("DATA/outputs/wave_storage_core_harmonised_v1", "R06_wave7MW_batt2x.nc"),
    "R03": ("DATA/outputs/wave_storage_core_harmonised_v1", "R03_wave0MW_batt3x.nc"),
    "R04": ("DATA/outputs/wave_storage_core_harmonised_v1", "R04_wave5MW_batt3x.nc"),
    "R07": ("DATA/outputs/wave_storage_core_harmonised_v1", "R07_wave7MW_batt3x.nc"),
    "R08": ("DATA/outputs/wave_storage_scaling_v1", "R08_wave15MW_batt2x.nc"),
    "R09": ("DATA/outputs/wave_storage_scaling_v1", "R09_wave30MW_batt2x.nc"),
    "R10": ("DATA/outputs/wave_storage_scaling_v1", "R10_wave15MW_batt3x.nc"),
    "R11": ("DATA/outputs/wave_storage_scaling_v1", "R11_wave30MW_batt3x.nc"),
    "R12": ("DATA/outputs/wave_storage_scaling_v1", "R12_wave0MW_batt4x.nc"),
    "R13": ("DATA/outputs/wave_storage_scaling_v1", "R13_wave5MW_batt4x.nc"),
    "R14": ("DATA/outputs/wave_storage_scaling_v1", "R14_wave7MW_batt4x.nc"),
    "R15": ("DATA/outputs/wave_storage_scaling_v1", "R15_wave15MW_batt4x.nc"),
    "R16": ("DATA/outputs/wave_storage_scaling_v1", "R16_wave30MW_batt4x.nc"),
}
OUT_DIR = "DATA/outputs/full_year_ac_screening"


def screen_scenario_full_year(scenario_id, nc_path, out_dir=OUT_DIR):
    print(f"\n{'='*100}\n{scenario_id}: {nc_path}\n{'='*100}")
    t0 = time.time()

    network = pypsa.Network()
    network.import_from_netcdf(nc_path)

    # Same principle as your critical-hour version: give EVERY generator
    # (including Slack) its LOPF dispatch as p_set, across ALL snapshots
    # at once. pf() then holds non-Slack generators fixed and computes
    # the Slack adjustment needed to balance losses/reactive power.
    lopf_gen_p = network.generators_t.p.copy()
    lopf_su_p = network.storage_units_t.p.copy()
    lopf_load_p = network.get_switchable_as_dense("Load", "p_set")

    network.generators_t.p_set = lopf_gen_p
    network.loads_t.p_set = lopf_load_p
    network.storage_units_t.p_set = lopf_su_p
    if not network.links.empty:
        network.links_t.p_set = network.links_t.p0.copy()
    network.generators.loc["Slack_generator", "control"] = "Slack"

    # Effective line/transformer capacity (same convention as your other
    # scripts: s_nom_opt for extendable branches, s_nom otherwise)
    line_capacity = network.lines["s_nom"].copy()
    if "s_nom_extendable" in network.lines.columns:
        ext = network.lines["s_nom_extendable"].fillna(False)
        if ext.any():
            line_capacity.loc[ext] = network.lines.loc[ext, "s_nom_opt"]
    line_s_max_pu = network.get_switchable_as_dense("Line", "s_max_pu")
    line_limit = line_s_max_pu.mul(line_capacity, axis=1)

    trafo_limit = pd.DataFrame()
    if not network.transformers.empty:
        trafo_capacity = network.transformers["s_nom"].copy()
        if "s_nom_extendable" in network.transformers.columns:
            text = network.transformers["s_nom_extendable"].fillna(False)
            if text.any():
                trafo_capacity.loc[text] = network.transformers.loc[text, "s_nom_opt"]
        trafo_s_max_pu = network.get_switchable_as_dense("Transformer", "s_max_pu")
        trafo_limit = trafo_s_max_pu.mul(trafo_capacity, axis=1)

    # ---- ONE pf() call across all snapshots, not one per hour ----
    result = network.pf()
    converged = result["converged"]  # DataFrame: snapshots x sub_networks
    converged_all = converged.all(axis=1)  # per-hour: did every sub-network converge

    elapsed = time.time() - t0
    print(f"pf() across {len(network.snapshots)} snapshots finished in {elapsed:.1f}s "
          f"({elapsed/len(network.snapshots)*1000:.1f} ms/snapshot)")

    # ---- Per-hour voltage summary ----
    v = network.buses_t.v_mag_pu
    v_min_per_hour = v.min(axis=1)
    v_max_per_hour = v.max(axis=1)
    v_within_bounds = (v_min_per_hour >= 0.90) & (v_max_per_hour <= 1.10)

    # ---- Per-hour line/transformer loading (|S| both ends vs effective limit) ----
    def apparent_power(p0, q0, p1, q1):
        s0 = np.sqrt(p0**2 + q0**2)
        s1 = np.sqrt(p1**2 + q1**2)
        return pd.DataFrame(np.maximum(s0, s1), index=p0.index, columns=p0.columns)

    line_q0 = (network.lines_t.q0 if "q0" in network.lines_t.keys() and not network.lines_t.q0.empty
               else network.lines_t.p0 * 0)
    line_q1 = (network.lines_t.q1 if "q1" in network.lines_t.keys() and not network.lines_t.q1.empty
               else network.lines_t.p1 * 0)
    line_s = apparent_power(network.lines_t.p0, line_q0, network.lines_t.p1, line_q1)
    line_loading_pct = (line_s / line_limit.replace(0, np.nan)) * 100
    max_line_loading_per_hour = line_loading_pct.max(axis=1)
    worst_line_per_hour = line_loading_pct.idxmax(axis=1)

    if not network.transformers.empty:
        t_q0 = (network.transformers_t.q0
                if "q0" in network.transformers_t.keys() and not network.transformers_t.q0.empty
                else network.transformers_t.p0 * 0)
        t_q1 = (network.transformers_t.q1
                if "q1" in network.transformers_t.keys() and not network.transformers_t.q1.empty
                else network.transformers_t.p1 * 0)
        trafo_s = apparent_power(network.transformers_t.p0, t_q0, network.transformers_t.p1, t_q1)
        trafo_loading_pct = (trafo_s / trafo_limit.replace(0, np.nan)) * 100
        max_trafo_loading_per_hour = trafo_loading_pct.max(axis=1)
        worst_trafo_per_hour = trafo_loading_pct.idxmax(axis=1)
    else:
        max_trafo_loading_per_hour = pd.Series(0.0, index=network.snapshots)
        worst_trafo_per_hour = pd.Series("", index=network.snapshots)

    thermal_ok = (max_line_loading_per_hour <= 100.0) & (max_trafo_loading_per_hour <= 100.0)

    # ---- Slack adjustment vs LOPF, per hour ----
    slack_lopf = lopf_gen_p["Slack_generator"]
    slack_pf = network.generators_t.p["Slack_generator"]
    slack_adjustment = slack_pf - slack_lopf
    demand_per_hour = lopf_load_p.sum(axis=1)
    allowed_adjustment = np.maximum(1.0, 0.05 * demand_per_hour)
    slack_within_tolerance = slack_adjustment.abs() <= allowed_adjustment

    per_hour = pd.DataFrame({
        "scenario_id": scenario_id,
        "converged": converged_all,
        "v_min_pu": v_min_per_hour,
        "v_max_pu": v_max_per_hour,
        "voltage_within_bounds": v_within_bounds,
        "max_line_loading_pct": max_line_loading_per_hour,
        "worst_line": worst_line_per_hour,
        "max_trafo_loading_pct": max_trafo_loading_per_hour,
        "worst_trafo": worst_trafo_per_hour,
        "thermal_within_bounds": thermal_ok,
        "slack_adjustment_mw": slack_adjustment,
        "slack_within_tolerance": slack_within_tolerance,
        "hour_pass": converged_all & v_within_bounds & thermal_ok,
    })

    os.makedirs(out_dir, exist_ok=True)
    per_hour_path = f"{out_dir}/{scenario_id}_full_year_ac.csv"
    per_hour.to_csv(per_hour_path)
    print(f"Saved per-hour detail: {per_hour_path}")

    # ---- Scenario-level summary (this is what actually goes in the thesis) ----
    n = len(per_hour)
    exceedance_hours = per_hour.loc[~per_hour["thermal_within_bounds"]]
    summary = {
        "scenario_id": scenario_id,
        "hours_total": n,
        "hours_converged": int(converged_all.sum()),
        "pct_converged": round(100 * converged_all.mean(), 3),
        "hours_voltage_within_bounds": int(v_within_bounds.sum()),
        "pct_voltage_within_bounds": round(100 * v_within_bounds.mean(), 3),
        "v_min_observed": round(float(v_min_per_hour.min()), 4),
        "v_max_observed": round(float(v_max_per_hour.max()), 4),
        "hours_thermal_within_bounds": int(thermal_ok.sum()),
        "pct_thermal_within_bounds": round(100 * thermal_ok.mean(), 3),
        "n_thermal_exceedance_hours": len(exceedance_hours),
        "max_line_loading_observed_pct": round(float(max_line_loading_per_hour.max()), 2),
        "max_trafo_loading_observed_pct": round(float(max_trafo_loading_per_hour.max()), 2),
        "hours_slack_within_tolerance": int(slack_within_tolerance.sum()),
        "pct_slack_within_tolerance": round(100 * slack_within_tolerance.mean(), 3),
        "runtime_seconds": round(elapsed, 1),
    }
    return summary, per_hour


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    all_summaries = []

    for i, (scenario_id, (directory, filename)) in enumerate(FILES.items(), start=1):
        path = f"{directory}/{filename}"
        print(f"\n[{i}/{len(FILES)}] {scenario_id}")
        if not os.path.exists(path):
            print(f"  File not found: {path} -- skipping")
            continue

        summary, _ = screen_scenario_full_year(scenario_id, path)
        all_summaries.append(summary)

        # Incremental save -- same principle as your other batch scripts,
        # so a crash on scenario 12 doesn't lose scenarios 1-11.
        pd.DataFrame(all_summaries).to_csv(f"{OUT_DIR}/full_year_ac_summary.csv", index=False)

    final = pd.DataFrame(all_summaries)
    print("\n" + "=" * 100)
    print("FULL-YEAR AC SCREENING -- ALL SCENARIOS")
    print("=" * 100)
    print(final.to_string(index=False))
    print(f"\nSaved: {OUT_DIR}/full_year_ac_summary.csv")


if __name__ == "__main__":
    main()