from pathlib import Path
import yaml

CONFIG_DIR = Path.home() / ".setu-review"


def init_config(gitlab_pat: str, gitlab_url: str = "https://gitlab.com"):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    (CONFIG_DIR / "rules").mkdir(exist_ok=True)

    config = {
        "gitlab_pat": gitlab_pat,
        "gitlab_url": gitlab_url,
        "username": "pulkit28",
        "batch_size": 30,
    }

    with open(CONFIG_DIR / "config.yaml", "w") as f:
        yaml.dump(config, f, default_flow_style=False)

    return config


def load_config() -> dict:
    config_path = CONFIG_DIR / "config.yaml"
    if not config_path.exists():
        raise FileNotFoundError(
            "Config not found. Run: setu-review init"
        )
    with open(config_path) as f:
        return yaml.safe_load(f)
