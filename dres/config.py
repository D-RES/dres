from pathlib import Path
import pandas as pd
import yaml
import platformdirs



### Helper functions for config management

# Internal function to get user config directory
def _user_config_dir() -> Path:
    """Return cross-platform user config directory Path."""
    if platformdirs is not None:
        return Path(platformdirs.user_config_dir("dres", "D-RES"))
    return Path.home() / ".dres"

# Internal function to get path to config.yaml
def get_config_path() -> Path:
    """Get the path to the config.yaml file (ensuring parent exists)."""
    cfg_dir = _user_config_dir()
    cfg_dir.mkdir(parents=True, exist_ok=True)
    return cfg_dir / "config.yaml"

# Internal function to load config from config.yaml
def load_config():
    """Load configuration from config.yaml if it exists; return dict or None."""
    cfg_file = get_config_path()
    if not cfg_file.exists():
        return None
    if yaml is None:
        raise ImportError("PyYAML is required. Install with: pip install pyyaml")
    with open(cfg_file, "r") as f:
        cfg = yaml.safe_load(f) or {}

    # Normalize all path fields to POSIX style for portability
    try:
        paths = cfg.get("paths", {})
        for key, val in list(paths.items()):
            if isinstance(val, str) and val.strip():
                paths[key] = Path(val).expanduser().resolve().as_posix()
        cfg["paths"] = paths
    except Exception:
        # If normalization fails, return original cfg without raising
        pass

    return cfg

# Internal function to create config.yaml
def create_config_file(data_root: str = None):
    """
    Create config.yaml. If data_root is None, prompt via CLI.

    Args:
        data_root: Path to local data root.

    Returns:
        dict: The config that was written.
    """
    if yaml is None:
        raise ImportError("PyYAML is required. Install with: pip install pyyaml")

    if not data_root:
        default_base = Path.home()
        val = input(f"Enter path to data root [{default_base}]: ").strip()
        data_root = val or str(default_base)

    cfg = {
        "paths": {
            "data_root": str(Path(data_root).expanduser().resolve()),
        },
        "created": pd.Timestamp.now().isoformat(),
    }

    cfg_file = get_config_path()
    with open(cfg_file, "w") as f:
        yaml.safe_dump(cfg, f, sort_keys=False)
    return cfg

# Get or create config - intended use by initialisation of main DRES class
def get_or_create_config():
    """Return existing config or create it interactively if missing."""
    cfg = load_config()
    if cfg is not None:
        return cfg
    return create_config_file()

# Update data_root in config.yaml - functional tool for user 
def update_data_root(new_path: str):
    """
    Update the data_root path in config.yaml.

    Args:
        new_path: New path to set as data_root.

    Returns:
        dict: Updated config.
    """
    if yaml is None:
        raise ImportError("PyYAML is required. Install with: pip install pyyaml")

    cfg = load_config()
    if cfg is None:
        cfg = {"paths": {}}

    cfg.setdefault("paths", {})
    cfg["paths"]["data_root"] = Path(new_path).expanduser().resolve().as_posix()
    cfg["modified"] = pd.Timestamp.now().isoformat()

    cfg_file = get_config_path()
    with open(cfg_file, "w") as f:
        yaml.safe_dump(cfg, f, sort_keys=False)
    return cfg

