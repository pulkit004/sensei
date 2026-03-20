from click.testing import CliRunner
from sensei.cli import main


def test_review_invalid_url():
    runner = CliRunner()
    result = runner.invoke(main, ["review", "not-a-valid-url"])
    assert result.exit_code != 0 or "Invalid" in result.output


def test_full_cli_help():
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert "learn" in result.output
    assert "review" in result.output
    assert "init" in result.output
    assert "post" in result.output
