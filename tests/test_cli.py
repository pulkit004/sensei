from click.testing import CliRunner
from setu_review.cli import main


def test_cli_help():
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "setu-review" in result.output


def test_learn_command_exists():
    runner = CliRunner()
    result = runner.invoke(main, ["learn", "--help"])
    assert result.exit_code == 0


def test_review_command_exists():
    runner = CliRunner()
    result = runner.invoke(main, ["review", "--help"])
    assert result.exit_code == 0
