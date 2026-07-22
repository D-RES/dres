"""
extract_complementarity_data.py
────────────────────────────────
Builds complementarity_input_data.csv with four aligned columns:
  wind_pu, wave_pu, tidal_pu (all 0-1 normalised), demand_mw (MW)
Indexed by 8,760 hourly timestamps for 2019.

Wind is correctly weighted by n_turbines from assets.yaml to give
the true aggregate 55.4 MW fleet profile.
"""

import pandas as pd
import os
import yaml

# ── 1. Wave (already pu, 8760 rows) ──────────────────────────────
wave = pd.read_csv("DATA/inputs/wave_orkney_2019.csv")
wave['time'] = pd.to_datetime(wave['time'])
wave = wave.set_index('time')['power (pu)'].rename('wave_pu')

# ── 2. Tidal (pu, 8761 rows — trim to 2019 only) ─────────────────
tidal = pd.read_csv("DATA/inputs/tidal_orkney_2019.csv")
tidal['time'] = pd.to_datetime(tidal['time'])
tidal = tidal[tidal['time'] < '2020-01-01']
tidal = tidal.set_index('time')['power (pu)'].rename('tidal_pu')

# ── 3. Wind — read assets.yaml to get real turbine counts per farm ─
with open("DATA/inputs/assets.yaml", "r") as f:
    assets = yaml.safe_load(f)

windfarms = assets['WindFarms']
print(f"Found {len(windfarms)} wind farm entries in assets.yaml")

wind_total_p    = None
wind_total_pnom = 0

for farm_key, farm_info in windfarms.items():
    file_path  = os.path.join("DATA/inputs", farm_info['file'])
    n_turbines = farm_info['n_turbines']

    df = pd.read_csv(file_path)
    df['DateTime'] = pd.to_datetime(df['DateTime'], format='mixed', dayfirst=True)
    df = df.set_index('DateTime')

    max_power_per_turbine = df['ActivePower'].max()
    p_actual_per_turbine  = df['ActivePower']

    farm_p_total    = p_actual_per_turbine * n_turbines
    farm_pnom_total = max_power_per_turbine * n_turbines

    print(f"  {farm_key}: file={farm_info['file']}, n_turbines={n_turbines}, "
          f"p_nom/turbine={max_power_per_turbine:.2f}MW, farm_total_pnom={farm_pnom_total:.2f}MW")

    if wind_total_p is None:
        wind_total_p = farm_p_total.copy()
    else:
        wind_total_p = wind_total_p.add(farm_p_total, fill_value=0)

    wind_total_pnom += farm_pnom_total

wind_pu = (wind_total_p / wind_total_pnom).rename('wind_pu')
print(f"\nTotal wind p_nom (correctly weighted): {wind_total_pnom:.1f} MW")
print(f"(Compare to expected ~55.4 MW from earlier energy balance script)")

# ── 4. Demand (sum active power columns, keep in MW) ─────────────
demand = pd.read_csv("DATA/inputs/Load_Profile.csv")
demand['DateTime'] = pd.to_datetime(demand['DateTime'], format='mixed', dayfirst=True)
demand = demand.set_index('DateTime')

active_cols   = [c for c in demand.columns if '[MW]' in c]
demand_total  = demand[active_cols].sum(axis=1).rename('demand_mw')

# ── 5. Combine into single aligned dataframe ──────────────────────
combined = pd.concat([wind_pu, wave, tidal, demand_total], axis=1, sort=True)
combined.index.name = 'time'

print(f"\nCombined shape: {combined.shape}")
print(combined.head())
print(f"\nNaN check:\n{combined.isna().sum()}")

# ── 6. Save ───────────────────────────────────────────────────────
combined.to_csv("DATA/outputs/complementarity_input_data.csv")
print("\nSaved: DATA/outputs/complementarity_input_data.csv")