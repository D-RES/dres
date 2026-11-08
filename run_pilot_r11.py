"""
run_pilot_r11.py

Standalone pilot test: runs the full-year AC screening on R11 only, to
check timing and sanity of the results before committing to all 15
scenarios.

USAGE:
    python run_pilot_r11.py
"""

from run_full_year_ac_screening import screen_scenario_full_year

summary, per_hour = screen_scenario_full_year(
    "R11", "DATA/outputs/wave_storage_scaling_v1/R11_wave30MW_batt3x.nc"
)

print("\n\n===== PILOT RESULT =====")
print(summary)