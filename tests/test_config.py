from setu_review.config import load_config, init_config, CONFIG_DIR


def test_init_config_creates_directory(tmp_path, monkeypatch):
    config_dir = tmp_path / ".sensei"
    monkeypatch.setattr("setu_review.config.CONFIG_DIR", config_dir)
    # Pass username to skip GitLab API call
    init_config(gitlab_pat="glpat-test123", username="testuser")
    assert (config_dir / "config.yaml").exists()


def test_load_config_reads_values(tmp_path, monkeypatch):
    config_dir = tmp_path / ".sensei"
    monkeypatch.setattr("setu_review.config.CONFIG_DIR", config_dir)
    init_config(gitlab_pat="glpat-test123", username="testuser")
    config = load_config()
    assert config["gitlab_pat"] == "glpat-test123"
    assert config["gitlab_url"] == "https://gitlab.com"
    assert config["username"] == "testuser"


def test_load_config_env_var_overrides_pat(tmp_path, monkeypatch):
    config_dir = tmp_path / ".sensei"
    monkeypatch.setattr("setu_review.config.CONFIG_DIR", config_dir)
    init_config(gitlab_pat="glpat-from-file", username="testuser")
    monkeypatch.setenv("GITLAB_PAT", "glpat-from-env")
    config = load_config()
    assert config["gitlab_pat"] == "glpat-from-env"
