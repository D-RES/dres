"""
run_pf_crosscheck_baseline_1x.py

Runs validate_critical_hours_pf() -- the genuine nonlinear AC power flow
cross-check -- against the 5 NEW B01-B05 1x-storage reference scenarios,
extending the same critical-hour AC screening already completed for the
R01-R15 dissertation matrix.

This closes the gap the reviewer flagged: since the dissertation now
presents AC screening as applying systematically across the scenario
matrix, the new B01-B05 baseline extension needs the same targeted
critical-hour treatment -- otherwise an examiner could reasonably ask why
the new baseline was exempted from the electrical assessment.

This is a structural derivative of run_pf_crosscheck_all_scenarios.py --
same import, same per-hour method, same acceptance criteria, same
per-bus voltage export. The only difference is which files are checked.

*** SCOPE NOTE ***
This script performs the TARGETED 5-critical-hour screen only (peak
demand, highest line loading, highest battery charge/discharge, highest
renewable output) -- matching the FIRST stage of AC screening described in
Section 3.10. The dissertation's SECOND stage (full-year screening across
all 8,760 hours per scenario) is a separate script not built here; if you
already have that full-year script from your own earlier work, it should
be pointed at the same B01-B05 files below in the same way.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from validate_scenario import validate_critical_hours_pf
import pandas as pd

BASELINE_1X_DIR = "DATA/outputs/baseline_1x_scenarios_v1"
SUMMARY_OUT_DIR = "DATA/outputs"

FILES = {
    "B01": (BASELINE_1X_DIR, "B01_wave0MW_batt1x.nc"),
    "B02": (BASELINE_1X_DIR, "B02_wave5MW_batt1x.nc"),
    "B03": (BASELINE_1X_DIR, "B03_wave7MW_batt1x.nc"),
    "B04": (BASELINE_1X_DIR, "B04_wave15MW_batt1x.nc"),
    "B05": (BASELINE_1X_DIR, "B05_wave30MW_batt1x.nc"),
}


def main():
    summary_rows = []
    total = len(FILES)

    for i, (scenario_id, (directory, filename)) in enumerate(FILES.items(), start=1):
        path = f"{directory}/{filename}"
        print(f"\n{'#' * 100}")
        print(f"# [{i}/{total}] {scenario_id} (B-series 1x reference extension): {path}")
        print(f"{'#' * 100}")

        if not os.path.exists(path):
            print(f"[{scenario_id}] File not found at {path} -- skipping. Check that the full "
                  f"B01-B05 batch (run_baseline_1x_scenarios.py) has completed successfully.")
            summary_rows.append({
                "scenario": scenario_id, "pf_convergence_voltage_pass": None,
                "slack_adjustment_review_needed": None, "hours_checked": 0,
                "hours_within_slack_tolerance": None,
            })
            continue

        pf_result = validate_critical_hours_pf(
            path, export_bus_voltages_dir=f"{SUMMARY_OUT_DIR}/bus_voltages_baseline_1x"
        )

        summary_rows.append({
            "scenario": scenario_id,
            "pf_convergence_voltage_pass": pf_result["pass"],
            "slack_adjustment_review_needed": pf_result.get("slack_adjustment_review_needed"),
            "hours_checked": len(pf_result["hour_results"]),
            "hours_within_slack_tolerance": sum(pf_result.get("hour_slack_adjustment_ok", {}).values()),
        })

        # Save incrementally -- so completed results survive an interruption
        pd.DataFrame(summary_rows).to_csv(
            f"{SUMMARY_OUT_DIR}/nonlinear_pf_crosscheck_baseline_1x_summary.csv", index=False
        )

    summary_df = pd.DataFrame(summary_rows)

    print("\n" + "=" * 100)
    print("CONSOLIDATED NONLINEAR AC pf() CROSS-CHECK -- B01-B05 (1x REFERENCE EXTENSION)")
    print("=" * 100)
    print(summary_df.to_string(index=False))

    out_path = f"{SUMMARY_OUT_DIR}/nonlinear_pf_crosscheck_baseline_1x_summary.csv"
    summary_df.to_csv(out_path, index=False)
    print(f"\nSaved: {out_path}")

    if summary_df["pf_convergence_voltage_pass"].fillna(False).all():
        print("\nAll 5 B01-B05 scenarios: nonlinear AC pf() converged with voltages within bounds "
              "at every critical hour checked.")
    else:
        failed = summary_df.loc[~summary_df["pf_convergence_voltage_pass"].fillna(False), "scenario"].tolist()
        print(f"\n*** {len(failed)} scenario(s) did NOT pass convergence/voltage: {failed} -- investigate ***")
        print("*** these specifically before treating them as AC-feasible.                              ***")

    if summary_df["slack_adjustment_review_needed"].fillna(True).any():
        review_needed = summary_df.loc[summary_df["slack_adjustment_review_needed"].fillna(True), "scenario"].tolist()
        print(f"\nScenario(s) with at least one hour requiring Slack-adjustment review: {review_needed}")
        print("(This does not necessarily mean a problem -- check the per-hour AC-loss diagnostic printed")
        print("above for each; the R01-R15 scenarios showed this pattern too, consistently explained by")
        print("genuine AC losses.)")

    print("\n*** REMINDER: this covers the TARGETED 5-critical-hour screen only. ***")
    print("*** The full-year (8,760-hour) screen for B01-B05 is a separate step -- ***")
    print("*** see the module docstring for how to extend your existing full-year script. ***")


if __name__ == "__main__":
    main()