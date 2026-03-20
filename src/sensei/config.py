import os
from pathlib import Path
import yaml

CONFIG_DIR = Path.home() / ".sensei"


def init_config(gitlab_pat: str, gitlab_url: str = "https://gitlab.com", username: str = ""):
    import gitlab
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    (CONFIG_DIR / "rules").mkdir(exist_ok=True)

    # Derive username from GitLab API if not provided
    if not username:
        gl = gitlab.Gitlab(gitlab_url, private_token=gitlab_pat)
        gl.auth()
        username = gl.user.username

    config = {
        "gitlab_pat": gitlab_pat,
        "gitlab_url": gitlab_url,
        "username": username,
        "batch_size": 30,
    }

    config_path = CONFIG_DIR / "config.yaml"
    with open(config_path, "w") as f:
        yaml.dump(config, f, default_flow_style=False)

    # Restrict file permissions (owner only)
    config_path.chmod(0o600)

    return config


def load_config() -> dict:
    config_path = CONFIG_DIR / "config.yaml"
    if not config_path.exists():
        raise FileNotFoundError(
            "Config not found. Run: sensei init"
        )
    with open(config_path) as f:
        config = yaml.safe_load(f)

    # Allow env var override for PAT
    env_pat = os.environ.get("GITLAB_PAT")
    if env_pat:
        config["gitlab_pat"] = env_pat

    return config
