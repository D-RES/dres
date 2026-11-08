"""
run_full_year_ac_screening_baseline_1x.py

Full-year nonlinear AC power-flow screening for the 5 NEW B01-B05
1x-storage reference scenarios, extending the full-year screening already
completed for the R01-R15 dissertation matrix to this supervisor-requested
baseline extension.

Structural derivative of run_full_year_ac_screening.py -- identical method
(one pf() call across all 8,760 snapshots, same voltage and thermal
acceptance criteria, with the same Slack-adjustment diagnostic), applied
to the B01-B05 files instead. This closes
the second (full-year) stage of AC screening for the B-series, matching
what run_pf_crosscheck_baseline_1x.py already did for the first
(critical-hour) stage.

*** NO LEGACY/STUDY-ID AMBIGUITY HERE ***
Unlike the original R01-R15 full-year script (whose FILES dict keys are
LEGACY IDs that do NOT match the final dissertation Study IDs -- see
Table E.1), B01-B05 have no legacy numbering at all. The scenario_id
values used throughout this script ARE the labels to use directly in the
dissertation -- no translation step is needed for these five.
"""

import os
import time
import numpy as np
import pandas as pd
import pypsa

FILES = {
    "B01": ("DATA/outputs/baseline_1x_scenarios_v1", "B01_wave0MW_batt1x.nc"),
    "B02": ("DATA/outputs/baseline_1x_scenarios_v1", "B02_wave5MW_batt1x.nc"),
    "B03": ("DATA/outputs/baseline_1x_scenarios_v1", "B03_wave7MW_batt1x.nc"),
    "B04": ("DATA/outputs/baseline_1x_scenarios_v1", "B04_wave15MW_batt1x.nc"),
    "B05": ("DATA/outputs/baseline_1x_scenarios_v1", "B05_wave30MW_batt1x.nc"),
}
OUT_DIR = "DATA/outputs/full_year_ac_screening_baseline_1x"
TARGET_TRAFO = "86129 - 86130"  # the recurring full-year thermal constraint
                                 # already identified in the R01-R15 matrix --
                                 # tracked explicitly here for direct comparison
                                 # across 1x/2x/3x/4x storage


def screen_scenario_full_year(scenario_id, nc_path, out_dir=OUT_DIR):
    print(f"\n{'='*100}\n{scenario_id}: {nc_path}\n{'='*100}")
    t0 = time.time()

    network = pypsa.Network()
    network.import_from_netcdf(nc_path)

    lopf_gen_p = network.generators_t.p.copy()
    lopf_su_p = network.storage_units_t.p.copy()
    lopf_load_p = network.get_switchable_as_dense("Load", "p_set")

    network.generators_t.p_set = lopf_gen_p
    network.loads_t.p_set = lopf_load_p
    network.storage_units_t.p_set = lopf_su_p
    if not network.links.empty:
        network.links_t.p_set = network.links_t.p0.copy()
    network.generators.loc["Slack_generator", "control"] = "Slack"

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

    result = network.pf()
    converged = result["converged"]
    converged_all = converged.all(axis=1)

    elapsed = time.time() - t0
    print(f"pf() across {len(network.snapshots)} snapshots finished in {elapsed:.1f}s "
          f"({elapsed/len(network.snapshots)*1000:.1f} ms/snapshot)")

    v = network.buses_t.v_mag_pu
    v_min_per_hour = v.min(axis=1)
    v_max_per_hour = v.max(axis=1)
    v_within_bounds = (v_min_per_hour >= 0.90) & (v_max_per_hour <= 1.10)

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

        if TARGET_TRAFO not in trafo_loading_pct.columns:
            raise KeyError(
                f"Expected target transformer '{TARGET_TRAFO}' not found. "
                f"Check transformer naming before interpreting results."
            )
        target_trafo_loading_pct = trafo_loading_pct[TARGET_TRAFO]
        target_trafo_exceeds = target_trafo_loading_pct > 100.0
    else:
        max_trafo_loading_per_hour = pd.Series(0.0, index=network.snapshots)
        worst_trafo_per_hour = pd.Series("", index=network.snapshots)
        target_trafo_loading_pct = pd.Series(0.0, index=network.snapshots)
        target_trafo_exceeds = pd.Series(False, index=network.snapshots)

    thermal_ok = (max_line_loading_per_hour <= 100.0) & (max_trafo_loading_per_hour <= 100.0)

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
        "target_trafo_loading_pct": target_trafo_loading_pct,
        "target_trafo_exceeds_100pct": target_trafo_exceeds,
        "hour_pass": converged_all & v_within_bounds & thermal_ok,
    })

    os.makedirs(out_dir, exist_ok=True)
    per_hour_path = f"{out_dir}/{scenario_id}_full_year_ac.csv"
    per_hour.to_csv(per_hour_path)
    print(f"Saved per-hour detail: {per_hour_path}")

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
        "target_trafo": TARGET_TRAFO,
        "target_trafo_exceedance_hours": int(target_trafo_exceeds.sum()),
        "target_trafo_exceedance_pct": round(100 * target_trafo_exceeds.mean(), 3),
        "target_trafo_max_loading_pct": round(float(target_trafo_loading_pct.max()), 2),
        "runtime_seconds": round(elapsed, 1),
    }
    return summary, per_hour


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    all_summaries = []

    for i, (scenario_id, (directory, filename)) in enumerate(FILES.items(), start=1):
        path = f"{directory}/{filename}"
        print(f"\n[{i}/{len(FILES)}] {scenario_id} (B-series 1x reference extension)")
        if not os.path.exists(path):
            print(f"  File not found: {path} -- skipping. Check that run_baseline_1x_scenarios.py "
                  f"has completed successfully.")
            continue

        summary, _ = screen_scenario_full_year(scenario_id, path)
        all_summaries.append(summary)

        pd.DataFrame(all_summaries).to_csv(f"{OUT_DIR}/full_year_ac_summary_baseline_1x.csv", index=False)

    final = pd.DataFrame(all_summaries)
    print("\n" + "=" * 100)
    print("FULL-YEAR AC SCREENING -- B01-B05 (1x REFERENCE EXTENSION)")
    print("=" * 100)
    print(final.to_string(index=False))
    print(f"\nSaved: {OUT_DIR}/full_year_ac_summary_baseline_1x.csv")
    print("\nNOTE: scenario_id values here (B01-B05) ARE the correct labels to use directly")
    print("in the dissertation -- unlike the original R-series full-year script, there is no")
    print("legacy-ID translation step needed for these five.")


if __name__ == "__main__":
    main()
    