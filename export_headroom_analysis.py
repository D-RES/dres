"""
export_headroom_analysis.py

Post-processing analysis: for a solved LOPF scenario (import-only mainland
boundary, Slack_generator p_min_pu=0), screens how much of the modelled
renewable curtailment coincided with available mainland-interconnector
transfer headroom -- distinguishing the portion that would first displace
modelled mainland IMPORT from the portion representing additional export
potential, rather than labelling the whole accommodated
quantity as "exportable".

This is explicitly an UPPER-BOUND screen, not a redispatch simulation:
cable headroom alone does not prove curtailed generation could physically
reach the mainland without encountering another internal Orkney network
constraint (as the full-year AC screening already demonstrated for
transformer 86129-86130).

METHOD, per hour t:

  Curtailment (Eq. 3.37, unchanged):
      C_t = available renewable generation_t - dispatched renewable generation_t

  Per-branch headroom toward the export-direction limit. For a branch with
  symmetric flow limit [-S_t, +S_t], where positive flow F_t denotes
  mainland-to-Orkney import direction, the maximum additional Orkney-side
  injection that could be accommodated before the branch reached its
  export-direction limit is:
      H_t = F_t + S_t
  (NOT 2*S_t - F_t -- these are only equal at F_t = S_t/2. Verified
  numerically: S=21.05, F=10 importing gives H=31.05 MW via F+S, not
  32.1 MW via 2S-F.)

  Per-circuit headroom is the minimum across that circuit's series line
  segments (weakest-link, upper-bound); total headroom is the sum of the
  two circuits:
      H_t = min(H_l for l in circuit_1) + min(H_l for l in circuit_2)

  Accommodatable curtailment (NOT "exportable" -- this is the portion the
  mainland-boundary state could absorb through EITHER reduced import OR
  increased export):
      A_t = min(C_t, H_t)

  This is then split into two physically distinct quantities:
      D_t (import displacement) = min(A_t, I_t)   where I_t = current import
      X_t (additional export potential beyond import displacement) = A_t - D_t
      This remains an upper-bound POTENTIAL, not a confirmed outcome -- no
      redispatch has been performed to demonstrate these MW actually reach
      mainland Scotland through the internal network.

  Residual curtailment after the mainland-headroom screen (NOT "stranded" --
  only that this specific screen could not accommodate it):
      R_t = C_t - A_t
"""

import pypsa
import pandas as pd
import numpy as np
import os

INTERCONNECTOR_LINES = [
    "19330 - 86018", "86018 - 86170",
    "19330 - 86019", "86019 - 86171",
]
INTERCONNECTOR_S_NOM = 21.05  # MVA per line segment (modelled LOPF rating -- NOT
                               # to be silently equated with the commonly-reported
                               # ~40 MW real-world active-power transfer figure;
                               # 42.1 MVA combined derives from 40 MW / 0.95 pf).
                               # NOTE: this constant is documentation only -- the
                               # actual effective_rating used in the calculation is
                               # read directly from network.lines["s_nom"] (the
                               # network's own stored values), which is more robust
                               # than hardcoding it here.

ASSUMED_POWER_FACTOR = 0.95  # SAME conversion factor already used throughout this
                              # project to derive 21.05 MVA from 40 MW (40 MW / 2
                              # circuits / 0.95 pf = 21.05 MVA per circuit). Applying
                              # this factor to the model's own s_nom values, rather
                              # than hardcoding "40", correctly handles any asymmetry
                              # between the two circuits' actual stored ratings.

EXPECTED_TOPOLOGY = {
    # Verified directly against the production network (not assumed):
    # bus0/bus1 store bus NAMES, not bus numbers. THSO3- is confirmed as
    # both the Slack_generator's bus and bus0 of both first-segment lines,
    # confirming bus0 is consistently the mainland side and the sign
    # convention (positive p0 = mainland-to-Orkney import) is correct.
    "19330 - 86018": ("THSO3-", "THU-3L5"),
    "86018 - 86170": ("THU-3L5", "STHHOY3A"),
    "19330 - 86019": ("THSO3-", "THU-6L5"),
    "86019 - 86171": ("THU-6L5", "STHHOY3B"),
}

EXPECTED_WIND_CAPACITY_MW = 55.4
# Tolerance set to 0.05 MW, not 1e-4 -- "55.4 MW" is a rounded figure used
# throughout the dissertation; the true precise installed capacity is
# approximately 55.42 MW (confirmed earlier in this project via
# check_network_wind_representation.py). A tight tolerance against the
# rounded figure would incorrectly fail a correctly-configured network.
WIND_CAPACITY_TOLERANCE = 0.05

OUTPUT_DIR = "DATA/outputs/export_headroom"


def compute_export_headroom_analysis(nc_file_path, scenario_label=None, power_factor=None):
    """
    Runs the export-headroom screen on one solved scenario .nc file.

    power_factor: if None (default), uses the model's own s_nom values
        directly -- the LOPF-internal apparent-power (MVA) bound, giving
        results consistent with what the linear optimisation itself saw.
        If set (e.g. 0.95), scales EVERY line's effective_rating by this
        factor before recomputing the full per-circuit weakest-link
        headroom logic -- giving an active-power sensitivity benchmark for
        comparison with the approximately 40 MW mainland-transfer
        capability. This is NOT a flat cap applied to the final combined
        total; it correctly rescales each line individually first, so any
        asymmetry between the two circuits' actual flows/ratings is still
        handled correctly.

    Returns (hourly_df, summary_dict).
    """
    network = pypsa.Network()
    network.import_from_netcdf(nc_file_path)

    if scenario_label is None:
        scenario_label = os.path.splitext(os.path.basename(nc_file_path))[0]
        print(f"  [WARNING] No scenario_label given -- defaulting to filename-derived label "
              f"'{scenario_label}'. If this file was produced by a LEGACY scenario script, this "
              f"label may NOT match the final dissertation Study ID (see Table E.1) -- verify "
              f"before using this label in any results table.")

    # ── Guard: confirm the import-only bound still holds ─────────────────
    slack_p_min_pu = float(network.generators.loc["Slack_generator", "p_min_pu"])
    if not np.isclose(slack_p_min_pu, 0.0):
        raise ValueError(
            f"[{scenario_label}] Slack_generator p_min_pu = {slack_p_min_pu}, not 0.0. "
            f"This script assumes the import-only production model documented in Section "
            f"3.11 -- if this network has since been changed to allow negative Slack dispatch, "
            f"this export-headroom SCREEN is no longer the correct analysis; the model would "
            f"already be optimising export directly. Investigate before proceeding."
        )

    # ── Guard: verify interconnector line topology/orientation explicitly,
    #    rather than assuming the sign convention from line naming ────────
    for line, (expected_bus0, expected_bus1) in EXPECTED_TOPOLOGY.items():
        if line not in network.lines.index:
            raise KeyError(f"[{scenario_label}] Expected interconnector line '{line}' not found.")
        actual_bus0 = network.lines.at[line, "bus0"]
        actual_bus1 = network.lines.at[line, "bus1"]
        if actual_bus0 != expected_bus0 or actual_bus1 != expected_bus1:
            raise ValueError(
                f"[{scenario_label}] {line}: expected {expected_bus0}->{expected_bus1}, "
                f"found {actual_bus0}->{actual_bus1}. Sign convention assumption is invalid; "
                f"do not trust headroom results without correcting the orientation logic."
            )

    # ── Guard: confirm the renewable generator set matches the dissertation's
    #    own definitions before trusting the curtailment total ────────────
    wind_gens = [g for g in network.generators.index if "WindFarm" in g]
    wind_capacity = network.generators.loc[wind_gens, "p_nom"].sum()
    if not np.isclose(wind_capacity, EXPECTED_WIND_CAPACITY_MW, atol=WIND_CAPACITY_TOLERANCE):
        raise ValueError(
            f"[{scenario_label}] Identified wind capacity is {wind_capacity:.4f} MW, "
            f"expected {EXPECTED_WIND_CAPACITY_MW} MW. Wind generator identification via "
            f"'WindFarm' substring may not match this network -- investigate alt_name usage."
        )
    if "Wave Generator" not in network.generators.index:
        raise KeyError(f"[{scenario_label}] 'Wave Generator' not found in network.generators.")
    if "EDAY Tidal Generator" not in network.generators.index:
        raise KeyError(f"[{scenario_label}] 'EDAY Tidal Generator' not found in network.generators.")

    generator_weights = network.snapshot_weightings["generators"].reindex(network.snapshots).astype(float)

    # ── Step 1: renewable curtailment per hour, SAME definition as Eq. 3.37 ──
    generator_p_max_pu = network.get_switchable_as_dense("Generator", "p_max_pu")
    renewable_gens = [g for g in network.generators.index
                      if ("WindFarm" in g or "Wave" in g or "Tidal" in g)]

    availability = pd.DataFrame({
        g: (generator_p_max_pu[g].clip(lower=0.0, upper=1.0) * float(network.generators.loc[g, "p_nom"]))
        for g in renewable_gens
    }).sum(axis=1)

    dispatch = network.generators_t.p[renewable_gens].sum(axis=1)
    curtailment_mw = (availability - dispatch).clip(lower=0.0)

    # ── Step 2: real interconnector flows and effective ratings, per line ──
    line_capacity = network.lines["s_nom"].astype(float)
    line_s_max_pu_dense = network.get_switchable_as_dense("Line", "s_max_pu")
    line_s_max_pu = line_s_max_pu_dense.reindex(
        index=network.snapshots, columns=INTERCONNECTOR_LINES
    ).fillna(1.0).astype(float)

    # This is the TRUE model-internal rating -- what the LOPF itself was
    # actually bounded by. This is what solved flows must be validated
    # against, regardless of what basis is later used for the headroom
    # calculation -- validating against a rescaled benchmark here would
    # incorrectly flag legitimate LOPF flows as violations.
    true_lopf_effective_rating = line_s_max_pu.mul(line_capacity[INTERCONNECTOR_LINES], axis=1)

    p0 = network.lines_t.p0[INTERCONNECTOR_LINES]

    # ── Guard: confirm no solved flow already exceeds the TRUE LOPF rating ──
    violation = p0.abs() - true_lopf_effective_rating
    max_violation = float(violation.max().max())
    if max_violation > 1e-4:
        raise ValueError(
            f"[{scenario_label}] Interconnector flow exceeds effective rating by "
            f"{max_violation:.6f} MW. Investigate before trusting headroom results."
        )

    # Now derive the rating actually used for the HEADROOM calculation --
    # either the true LOPF basis unchanged, or a properly rescaled
    # active-power benchmark, applied per-line before the weakest-link logic.
    if power_factor is not None:
        effective_rating = true_lopf_effective_rating * power_factor
        rating_basis = (
            f"active-power sensitivity benchmark (pf={power_factor}; "
            f"approximately 20 MW per circuit / 40 MW combined)"
        )
        # Confirm the existing solved LOPF flows don't already exceed this
        # tighter sensitivity benchmark -- if they did, the headroom
        # calculation below would be starting from outside the physical
        # benchmark we're trying to apply, and the 0.95-pf sensitivity
        # could not be interpreted directly without further treatment.
        benchmark_violation = p0.abs() - effective_rating
        max_benchmark_violation = float(benchmark_violation.max().max())
        if max_benchmark_violation > 1e-4:
            raise ValueError(
                f"[{scenario_label}] Existing solved interconnector flow exceeds "
                f"the active-power benchmark by {max_benchmark_violation:.6f} MW. "
                f"The 0.95-pf sensitivity cannot be interpreted directly from this "
                f"LOPF solution without further treatment."
            )
    else:
        effective_rating = true_lopf_effective_rating
        rating_basis = (
            "model-internal branch limit derived from s_nom "
            "(21.05 MVA nominal rating per circuit)"
        )

    # ── Step 3: per-line headroom toward the export direction: H = F + S ──
    # (Not 2S - F -- see module docstring for the numerical distinction.)
    headroom_per_line = p0.add(effective_rating, axis=0).clip(lower=0.0)

    circuit_1_headroom = headroom_per_line[["19330 - 86018", "86018 - 86170"]].min(axis=1)
    circuit_2_headroom = headroom_per_line[["19330 - 86019", "86019 - 86171"]].min(axis=1)
    total_headroom_mw = circuit_1_headroom + circuit_2_headroom

    circuit_1_flow_mw = p0["19330 - 86018"]
    circuit_2_flow_mw = p0["19330 - 86019"]
    total_boundary_flow_mw = circuit_1_flow_mw + circuit_2_flow_mw

    # Use the dissertation's OWN defined metric for mainland import -- actual
    # Slack_generator dispatch (Section 3.11: "positive Slack dispatch
    # classified as mainland import") -- not a re-derivation from line flows.
    slack_p = (
        network.generators_t.p["Slack_generator"]
        .reindex(network.snapshots)
        .fillna(0.0)
        .astype(float)
    )
    current_import_mw = slack_p.clip(lower=0.0)
    current_export_mw = (-slack_p).clip(lower=0.0)

    # Validation diagnostic only: in a lossless LOPF with no other material
    # injection/withdrawal at the mainland bus, the summed boundary line flow
    # should be essentially identical to Slack dispatch. A nonzero residual
    # flags something worth investigating before trusting the headroom split.
    boundary_slack_residual_mw = total_boundary_flow_mw - slack_p

    # Second empirical confirmation (beyond p_min_pu=0) that the production
    # solution never actually exported: should be essentially zero.
    max_negative_slack_mw = float((-slack_p.clip(upper=0)).max())

    # ── Step 4: accommodatable curtailment, then split into import-
    #    displacement vs additional export potential beyond that displacement ──
    accommodatable_mw = pd.concat([curtailment_mw, total_headroom_mw], axis=1).min(axis=1)
    import_displacement_mw = pd.concat([accommodatable_mw, current_import_mw], axis=1).min(axis=1)
    additional_export_potential_mw = accommodatable_mw - import_displacement_mw
    residual_after_headroom_mw = curtailment_mw - accommodatable_mw

    hourly_df = pd.DataFrame({
        "snapshot": network.snapshots,
        "curtailment_mw": curtailment_mw.values,
        "circuit_1_flow_mw": circuit_1_flow_mw.values,
        "circuit_2_flow_mw": circuit_2_flow_mw.values,
        "total_mainland_boundary_flow_mw": total_boundary_flow_mw.values,
        "slack_p_mw": slack_p.values,
        "boundary_slack_residual_mw": boundary_slack_residual_mw.values,
        "current_import_mw": current_import_mw.values,
        "current_export_mw": current_export_mw.values,
        "export_headroom_mw": total_headroom_mw.values,
        "mainland_accommodatable_mw": accommodatable_mw.values,
        "import_displacement_mw": import_displacement_mw.values,
        "additional_export_potential_mw": additional_export_potential_mw.values,
        "residual_after_headroom_mw": residual_after_headroom_mw.values,
    })

    # Weighted-hours safeguard: this is a complete 8,760-hour model, so
    # weights should all be 1.0 -- assert this rather than silently rely on
    # ordinary row counts being equivalent to weighted counts.
    assert np.allclose(generator_weights.values, 1.0), (
        f"[{scenario_label}] Snapshot weights are not all 1.0 -- "
        f"hours_with_any_curtailment would not equal weighted hours."
    )

    def weighted_sum(series):
        return float(pd.Series(series).mul(generator_weights.values).sum())

    total_curtailment_mwh = weighted_sum(curtailment_mw.values)
    total_accommodatable_mwh = weighted_sum(accommodatable_mw.values)
    total_import_displacement_mwh = weighted_sum(import_displacement_mw.values)
    total_additional_export_mwh = weighted_sum(additional_export_potential_mw.values)
    total_residual_mwh = weighted_sum(residual_after_headroom_mw.values)

    # Identity checks (should hold to numerical precision by construction --
    # verified explicitly here as an auditable sanity check, not assumed):
    #   A = D + X   (accommodatable = import displacement + additional export)
    #   C = A + R   (curtailment = accommodatable + residual)
    identity_1_diff = abs(total_accommodatable_mwh - (total_import_displacement_mwh + total_additional_export_mwh))
    identity_2_diff = abs(total_curtailment_mwh - (total_accommodatable_mwh + total_residual_mwh))
    assert identity_1_diff < 1e-3, f"[{scenario_label}] A = D + X identity failed: diff={identity_1_diff:.6f} MWh"
    assert identity_2_diff < 1e-3, f"[{scenario_label}] C = A + R identity failed: diff={identity_2_diff:.6f} MWh"

    summary = {
        "scenario": scenario_label,
        "rating_basis": rating_basis,
        "total_curtailment_mwh": total_curtailment_mwh,
        "mainland_accommodatable_mwh": total_accommodatable_mwh,
        "mainland_accommodatable_pct": (
            100 * total_accommodatable_mwh / total_curtailment_mwh if total_curtailment_mwh > 0 else np.nan
        ),
        "import_displacement_mwh": total_import_displacement_mwh,
        "additional_export_potential_mwh": total_additional_export_mwh,
        "residual_after_headroom_mwh": total_residual_mwh,
        "max_hourly_curtailment_mw": float(curtailment_mw.max()),
        "max_hourly_additional_export_potential_mw": float(additional_export_potential_mw.max()),
        "hours_with_any_curtailment": int((curtailment_mw > 1e-4).sum()),
        "hours_curtailment_fully_accommodatable": int(
            ((curtailment_mw > 1e-4) & (residual_after_headroom_mw < 1e-4)).sum()
        ),
        "max_abs_boundary_slack_residual_mw": float(boundary_slack_residual_mw.abs().max()),
        "max_negative_slack_mw": max_negative_slack_mw,
        "identity_check_A_eq_D_plus_X_diff_mwh": identity_1_diff,
        "identity_check_C_eq_A_plus_R_diff_mwh": identity_2_diff,
    }

    return hourly_df, summary


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Each entry: (file_path, explicit scenario_label, human-readable note)
    # Labels are ALWAYS set explicitly -- never left to default from a
    # filename, per the R11/R12 legacy-ID lesson learned earlier.
    SCENARIOS_TO_RUN = [
        (
            "DATA/outputs/wave_storage_scaling_v1/R12_wave0MW_batt4x.nc",
            "R11_4x_0MWwave_legacyR12",
            "Already-validated case (Table E.1: Study ID R11 = legacy R12, 0 MW, 4x)",
        ),
        (
            "DATA/outputs/wave_storage_scaling_v1/R09_wave30MW_batt2x.nc",
            "R05_2x_30MWwave_legacyR09",
            "Highest-curtailment case from the original 15 (Table E.1: Study ID R05 = "
            "legacy R09, 30 MW wave, 2x -- smallest battery paired with highest wave "
            "capacity, i.e. least storage available to absorb the largest surplus)",
        ),
        (
            "DATA/outputs/baseline_1x_scenarios_v1/B01_wave0MW_batt1x.nc",
            "B01_1x_0MWwave",
            "Supervisor-relevant: 1x inherited-model reference case, 0 MW wave",
        ),
        (
            "DATA/outputs/baseline_1x_scenarios_v1/B02_wave5MW_batt1x.nc",
            "B02_1x_5MWwave",
            "Supervisor-relevant: 1x reference case, 5 MW near-term wave case",
        ),
        (
            "DATA/outputs/baseline_1x_scenarios_v1/B03_wave7MW_batt1x.nc",
            "B03_1x_7MWwave",
            "1x reference case, 7 MW intermediate wave case",
        ),
        (
            "DATA/outputs/baseline_1x_scenarios_v1/B04_wave15MW_batt1x.nc",
            "B04_1x_15MWwave",
            "1x reference case, 15 MW intermediate wave case",
        ),
        (
            "DATA/outputs/baseline_1x_scenarios_v1/B05_wave30MW_batt1x.nc",
            "B05_1x_30MWwave",
            "Supervisor-relevant: 1x reference case, 30 MW upper wave case",
        ),
    ]

    all_summaries = []

    for file_path, scenario_label, note in SCENARIOS_TO_RUN:
        print("#" * 100)
        print(f"# {scenario_label}  --  {note}")
        print(f"# File: {file_path}")
        print("#" * 100 + "\n")

        for label_suffix, power_factor in [("model_MVA_basis", None), ("active_power_MW_basis", ASSUMED_POWER_FACTOR)]:
            run_label = f"{scenario_label}_{label_suffix}"
            hourly_df, summary = compute_export_headroom_analysis(
                file_path, scenario_label=run_label, power_factor=power_factor
            )
            summary["note"] = note
            all_summaries.append(summary)

            print("=" * 100)
            print(f"MAINLAND-HEADROOM CURTAILMENT SCREEN -- {summary['scenario']}")
            print(f"Rating basis: {summary['rating_basis']}")
            print("=" * 100)
            for k, v in summary.items():
                if isinstance(v, float):
                    print(f"  {k}: {v:,.2f}")
                else:
                    print(f"  {k}: {v}")
            print()

            hourly_out = f"{OUTPUT_DIR}/{summary['scenario']}_export_headroom_hourly.csv"
            hourly_df.to_csv(hourly_out, index=False)
            print(f"Saved hourly detail: {hourly_out}\n")

    summary_df = pd.DataFrame(all_summaries)
    summary_out = f"{OUTPUT_DIR}/export_headroom_summary_complete_v1.csv"
    summary_df.to_csv(summary_out, index=False)
    print(f"\nSaved combined summary (all scenarios, both rating bases): {summary_out}")

    print("\nNOTE: this is an UPPER-BOUND screen based on interconnector headroom only.")
    print("It does NOT confirm curtailed generation could physically reach the mainland")
    print("without encountering an internal Orkney network constraint (cf. the transformer")
    print("86129-86130 thermal exceedances already found in the full-year AC screen).")
    print("\nTWO rating bases are reported above, deliberately: the model-internal LOPF")
    print("apparent-power (MVA) bound is what the linear optimisation itself was actually")
    print("constrained by; the active-power (MW) basis, derived by applying the SAME 0.95")
    print("power-factor conversion already used elsewhere in this project, provides an")
    print("active-power sensitivity benchmark for comparison with the approximately 40 MW")
    print("reported mainland-transfer capability. Do not silently equate 42.1 MVA")
    print("with 42.1 MW when writing this up.")


if __name__ == "__main__":
    main()