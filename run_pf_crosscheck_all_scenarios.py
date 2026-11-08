"""
run_pf_crosscheck_all_scenarios.py

Runs validate_critical_hours_pf() (the genuine nonlinear AC power flow
cross-check) against ALL 15 scenario .nc files -- completing the grid
constraints screening described as a placeholder in Section 3.10 of the
methodology, and extending the nonlinear AC feasibility check we previously
only completed for R01.

This is the only way to actually KNOW whether the remaining 14 scenarios
are AC-feasible -- the LOPF-level validation (optimisation_validation_pass)
does NOT confirm this on its own, since optimize() uses a linearized,
lossless approximation that never checks voltages, reactive power, or real
line/transformer losses.

Scenario files are split across two directories, reflecting how the final
15-scenario dataset was actually built:
    R01, R02, R06, R03, R04, R07  -> the HARMONISED six-scenario rerun
                                      (confirmed 84/84 metrics match the
                                      original six-scenario results, at
                                      1e-6 tolerance)
    R08-R16                       -> the nine-scenario scaling study,
                                      completing the 3x5 wave-battery grid
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from validate_scenario import validate_critical_hours_pf
import pandas as pd

HARMONISED_DIR = "DATA/outputs/wave_storage_core_harmonised_v1"
SCALING_DIR = "DATA/outputs/wave_storage_scaling_v1"
SUMMARY_OUT_DIR = "DATA/outputs"

FILES = {
    # -- Harmonised six-scenario dataset --
    "R01": (HARMONISED_DIR, "R01_wave0MW_batt2x.nc"),
    "R02": (HARMONISED_DIR, "R02_wave5MW_batt2x.nc"),
    "R06": (HARMONISED_DIR, "R06_wave7MW_batt2x.nc"),
    "R03": (HARMONISED_DIR, "R03_wave0MW_batt3x.nc"),
    "R04": (HARMONISED_DIR, "R04_wave5MW_batt3x.nc"),
    "R07": (HARMONISED_DIR, "R07_wave7MW_batt3x.nc"),
    # -- Nine-scenario scaling dataset (completes the 3x5 grid) --
    "R08": (SCALING_DIR, "R08_wave15MW_batt2x.nc"),
    "R09": (SCALING_DIR, "R09_wave30MW_batt2x.nc"),
    "R10": (SCALING_DIR, "R10_wave15MW_batt3x.nc"),
    "R11": (SCALING_DIR, "R11_wave30MW_batt3x.nc"),
    "R12": (SCALING_DIR, "R12_wave0MW_batt4x.nc"),
    "R13": (SCALING_DIR, "R13_wave5MW_batt4x.nc"),
    "R14": (SCALING_DIR, "R14_wave7MW_batt4x.nc"),
    "R15": (SCALING_DIR, "R15_wave15MW_batt4x.nc"),
    "R16": (SCALING_DIR, "R16_wave30MW_batt4x.nc"),
}


def main():
    summary_rows = []
    total = len(FILES)

    for i, (scenario_id, (directory, filename)) in enumerate(FILES.items(), start=1):
        path = f"{directory}/{filename}"
        print(f"\n{'#' * 100}")
        print(f"# [{i}/{total}] {scenario_id}: {path}")
        print(f"{'#' * 100}")

        if not os.path.exists(path):
            print(f"[{scenario_id}] File not found at {path} -- skipping. Check the directory/filename "
                  f"match what your scenario scripts actually saved.")
            summary_rows.append({
                "scenario": scenario_id, "pf_convergence_voltage_pass": None,
                "slack_adjustment_review_needed": None, "hours_checked": 0,
                "hours_within_slack_tolerance": None,
            })
            continue

        pf_result = validate_critical_hours_pf(path, export_bus_voltages_dir=f"{SUMMARY_OUT_DIR}/bus_voltages")

        summary_rows.append({
            "scenario": scenario_id,
            "pf_convergence_voltage_pass": pf_result["pass"],
            "slack_adjustment_review_needed": pf_result.get("slack_adjustment_review_needed"),
            "hours_checked": len(pf_result["hour_results"]),
            "hours_within_slack_tolerance": sum(pf_result.get("hour_slack_adjustment_ok", {}).values()),
        })

        # Save incrementally -- so completed results survive an interruption
        # partway through all 15 (each scenario runs 5 nonlinear pf() solves,
        # so this is a genuinely time-consuming batch).
        pd.DataFrame(summary_rows).to_csv(f"{SUMMARY_OUT_DIR}/nonlinear_pf_crosscheck_summary.csv", index=False)

    summary_df = pd.DataFrame(summary_rows)

    print("\n" + "=" * 100)
    print("CONSOLIDATED NONLINEAR AC pf() CROSS-CHECK -- ALL 15 SCENARIOS")
    print("=" * 100)
    print(summary_df.to_string(index=False))

    out_path = f"{SUMMARY_OUT_DIR}/nonlinear_pf_crosscheck_summary.csv"
    summary_df.to_csv(out_path, index=False)
    print(f"\nSaved: {out_path}")

    if summary_df["pf_convergence_voltage_pass"].fillna(False).all():
        print("\nAll 15 scenarios: nonlinear AC pf() converged with voltages within bounds at every "
              "critical hour checked.")
    else:
        failed = summary_df.loc[~summary_df["pf_convergence_voltage_pass"].fillna(False), "scenario"].tolist()
        print(f"\n*** {len(failed)} scenario(s) did NOT pass convergence/voltage: {failed} -- investigate ***")
        print("*** these specifically before treating them as AC-feasible.                              ***")

    if summary_df["slack_adjustment_review_needed"].fillna(True).any():
        review_needed = summary_df.loc[summary_df["slack_adjustment_review_needed"].fillna(True), "scenario"].tolist()
        print(f"\nScenario(s) with at least one hour requiring Slack-adjustment review: {review_needed}")
        print("(This does not necessarily mean a problem -- check the per-hour AC-loss diagnostic printed")
        print("above for each; R01 showed this too, and it was confirmed to be genuine AC losses.)")


if __name__ == "__main__":
    main()