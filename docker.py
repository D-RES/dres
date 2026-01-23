#%%
import subprocess
import os
from pathlib import Path

import dres

"""
Build a Docker image for local testing of DRES project.

"""

cfg = dres.config.get_or_create_config()
data_root = cfg.get("paths", {}).get("data_root")
if not data_root:
    raise ValueError(
        "DRES data_root is missing. Set it with: dres.config.update_data_root(<path>)"
    )

data_path = Path(data_root) / "inputs"
if not data_path.exists():
    raise FileNotFoundError(
        f"INPUT_DATA_PATH does not exist: {data_path}. "
        "Create it or update data_root in config."
    )

subprocess.run(
    [
        "docker", "build",
        "-f", "Dockerfile_local",
        "--build-context", f"inputs={str(data_path)}",
        "-t", f"dres:{dres.__version__}",
        "."
    ],
    check=True
)


# %%
