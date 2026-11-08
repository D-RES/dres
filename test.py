"""
check_topology.py
"""

import pypsa

network = pypsa.Network()
network.import_from_netcdf(
    "DATA/outputs/wave_storage_scaling_v1/R12_wave0MW_batt4x.nc"
)

INTERCONNECTOR_LINES = [
    "19330 - 86018",
    "86018 - 86170",
    "19330 - 86019",
    "86019 - 86171",
]

print("\nSlack generator bus:")
print(network.generators.loc["Slack_generator", "bus"])

print("\nActual bus0 / bus1 for each interconnector line:\n")
for line in INTERCONNECTOR_LINES:
    if line not in network.lines.index:
        print(f"  {line}: NOT FOUND in network.lines.index")
        continue

    bus0 = network.lines.at[line, "bus0"]
    bus1 = network.lines.at[line, "bus1"]

    print(f'  "{line}": ("{bus0}", "{bus1}"),')