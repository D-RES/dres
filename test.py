import pypsa
import pandas as pd

# Replace with one final solved scenario used in the AC screening
NETWORK_FILE = (
    "DATA/outputs/wave_storage_scaling_v1/"
    "R15_wave15MW_batt4x.nc"
)

n = pypsa.Network()
n.import_from_netcdf(NETWORK_FILE)

print("=" * 80)
print("GENERATOR IDENTIFICATION")
print("=" * 80)

selected = []

for name in n.generators.index:
    name_lower = name.lower()
    if any(term in name_lower for term in [
        "wave", "tidal", "gas", "slack"
    ]):
        selected.append(name)

# Add up to three representative wind generators
wind_generators = [
    name for name in n.generators.index
    if "windfarm" in name.lower()
]
selected.extend(wind_generators[:3])

selected = list(dict.fromkeys(selected))

static_columns = [
    column for column in [
        "bus",
        "control",
        "p_nom",
        "p_set",
        "q_set",
        "v_mag_pu_set",
    ]
    if column in n.generators.columns
]

print(n.generators.loc[selected, static_columns].to_string())

print("\n" + "=" * 80)
print("EFFECTIVE GENERATOR Q_SET")
print("=" * 80)

generator_q = n.get_switchable_as_dense("Generator", "q_set")

for name in selected:
    if name in generator_q.columns:
        q = generator_q[name].astype(float)
        print(
            f"{name}: "
            f"min={q.min():.6f}, "
            f"max={q.max():.6f}, "
            f"mean={q.mean():.6f}, "
            f"nonzero={(q.abs() > 1e-9).sum()}, "
            f"non-null={q.notna().sum()}"
        )
    else:
        print(f"{name}: no effective q_set column found")

print("\n" + "=" * 80)
print("LOAD REACTIVE POWER")
print("=" * 80)

load_q = n.get_switchable_as_dense("Load", "q_set").astype(float)

print("Load columns:", len(load_q.columns))
print("Minimum q_set:", load_q.min().min())
print("Maximum q_set:", load_q.max().max())
print("Non-zero values:", int((load_q.abs() > 1e-9).sum().sum()))
print("Null values:", int(load_q.isna().sum().sum()))

print("\n" + "=" * 80)
print("STORAGE REACTIVE SETTINGS")
print("=" * 80)

storage_columns = [
    column for column in [
        "bus",
        "control",
        "p_nom",
        "p_set",
        "q_set",
    ]
    if column in n.storage_units.columns
]

print(n.storage_units[storage_columns].to_string())

storage_q = n.get_switchable_as_dense(
    "StorageUnit", "q_set"
).astype(float)

print("\nEffective storage q_set summary:")
print(storage_q.agg(["min", "max", "mean"]).to_string())
print(
    "Non-zero storage q_set values:",
    int((storage_q.abs() > 1e-9).sum().sum())
)

print("\n" + "=" * 80)
print("CONTROL-TYPE COUNTS")
print("=" * 80)

if "control" in n.generators.columns:
    print("\nGenerators:")
    print(n.generators["control"].value_counts(dropna=False))

if "control" in n.storage_units.columns:
    print("\nStorage units:")
    print(n.storage_units["control"].value_counts(dropna=False))