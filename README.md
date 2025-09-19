# The 'dres' model

## Obtain the code as a developer

Clone this repository (it is recommended to use GitHub Desktop). In the event that more than one developer is using a cloud directory to store their development code (e.g. OneDrive), keep separate folders for each developer; do this by changing the target local directory prompted by GitHub Desktop from `dres` to `dres-XYZ` (swapping `XYZ` for your initials). This allows you exclusive access to the `.git` folder relating to your personal clone.

These instructions assume that your source code folder (`dres-XYZ`) sits alongside a folder called `DATA/inputs` containing your case study data. An empty `DATA/outputs` folder is also required for collecting model output files (see below).

```shell
# e.g.
path/to/folder/
├── DATA
│   ├── inputs
│   │   └── {data files}
│   └── outputs
├── dres-ABC
│   ├── .git
│   └── {source}
└── dres-XYZ
    ├── .git
    └── {source}
```

## Use the code interactively (e.g. Notebook format)

To use `dres` as a developer, create a virtual environment to install an editable version of `dres` (you can create a `venv` folder in your root user directory, or place the virtual environment anywhere you prefer, although preferably not on a cloud-linked folder as this will slow down your computer and consume cloud space unecessarily - a Venv can take up around 1GB)

To make a new venv on your local system:

```
python -m venv C:\Users\{XYZ}\venv\DRES
```

You should then 'activate' (move into) your virtual environment using:

```
C:\Users\{XYZ}\venv\DRES\Scripts\Activate.ps1
```

> **Note**
> 
> You can see your new blank environment by typing `pip list`, and can get rid of the pip update warning by typing `python.exe -m pip install --upgrade pip`.

To install an editable version of `dres`, from the root of this repository (i.e. where `setup.py` exists), type:

```
pip install -e .
```

> **Note**
>
> `pip list` will now show the full list of necessary packages for `dres`, including `dres` itself, pointing to where you have it located on your local system.


When you open and run a notebook from `case_studies`, select the `DRES` virtual environment as your Python kernel.


## Package the model for DAFNI

### Pre-deployment tests using Docker Desktop (optional)

1. Open a terminal within the location of your `dres` development folder (e.g. `dres-XYZ`, swapping `XYZ` for your initials).
2. Open `Dockerfile_local` and replace all instances of `COPY dres-PM/` to `COPY dres-{your initials}/`. Save `Dockerfile_local`.
3. Move up one directory level:
   ```
   cd ..
   ```
4. Generate the Docker Image (processing can take >30min in the first instance, ~5min on repeat usage). Run the follow (swapping `XYZ` for your initials, and swapping v0.1.3 for the current version):
   ```
   docker build -f dres-XYZ/Dockerfile_local . -t dres_v0.1.3_local
   ```

### Deployment on DAFNI

1. Open a terminal within the location of your `dres` development folder (e.g. `dres-XYZ`, swapping `XYZ` for your initials).
2. Generate the Docker Image (processing can take >30min in the first instance, ~5min on repeat usage). Run the follow (swapping v0.1.3 for the current version):
   ```
   docker build . -t dres_v0.1.3
   ```
3. Zip this new Docker Image using:
   ```
   docker save dres_v0.1.3 | gzip > dres_v0.1.3.tar.gz
   ```
   If you have issues using `gzip` on Windows, try using a virtual box or the Git Bash tool (https://git-scm.com/downloads).
4. Upload this new `.tar.gz` file to DAFNI.


