#%%
import subprocess
import os

import dres

"""
Build a Docker image for the DRES project.

"""

cfg = dres.config.get_or_create_config()
data_path = os.path.join(cfg['paths']['data_root'], 'inputs')

subprocess.run(
    [
        "docker", "build",
        "-f", "Dockerfile_local",
        "--build-arg", f"INPUT_DATA_PATH={data_path}",
        "-t", f"dres:{dres.__version__}",
        "."
    ],
    check=True
)

# %%
