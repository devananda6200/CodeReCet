import yaml
from pathlib import Path

def load_config(config_path):
    """
    Load YAML config file.
    """
    config_path = Path(config_path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    with open(config_path, 'r') as f:
        cfg = yaml.safe_load(f)
    return cfg
