from click.testing import CliRunner
from sensei.cli import main


def test_cli_help():
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "Sensei" in result.output


def test_learn_command_exists():
    runner = CliRunner()
    result = runner.invoke(main, ["learn", "--help"])
    assert result.exit_code == 0


def test_review_command_exists():
    runner = CliRunner()
    result = runner.invoke(main, ["review", "--help"])
    assert result.exit_code == 0


from unittest.mock import patch, MagicMock


def test_review_batch_command_exists():
    runner = CliRunner()
    result = runner.invoke(main, ["review-batch", "--help"])
    assert result.exit_code == 0
    assert "concurrency" in result.output
    assert "dry-run" in result.output
    assert "--file" in result.output


def test_review_batch_from_file(tmp_path):
    url_file = tmp_path / "urls.txt"
    url_file.write_text(
        "# MRs to review\n"
        "https://gitlab.com/org/proj/-/merge_requests/1\n"
        "\n"
        "https://gitlab.com/org/proj/-/merge_requests/2\n"
    )
    runner = CliRunner()
    result = runner.invoke(main, ["review-batch", "--file", str(url_file)])
    assert "Invalid MR URL" not in result.output


def test_review_batch_no_urls():
    runner = CliRunner()
    result = runner.invoke(main, ["review-batch"])
    assert result.exit_code != 0


def test_review_batch_rejects_invalid_urls():
    runner = CliRunner()
    result = runner.invoke(main, ["review-batch", "not-a-url"])
    assert result.exit_code != 0
    assert "Invalid" in result.output


def test_review_single_mr_returns_result_dict():
    mock_client = MagicMock()
    mock_client.get_mr_diff.return_value = {
        "title": "Fix bug", "description": "Fixes issue",
        "source_branch": "fix-bug", "target_branch": "main",
        "author": "testuser",
        "web_url": "https://gitlab.com/org/proj/-/merge_requests/1",
        "base_sha": "aaa", "head_sha": "bbb", "start_sha": "ccc",
        "files": [],
    }
    config = {"gitlab_url": "https://gitlab.com", "gitlab_pat": "fake", "batch_size": 30}

    from sensei.cli import _review_single_mr
    result = _review_single_mr(
        client=mock_client, config=config,
        project_path="org/proj", mr_iid=1,
        mr_url="https://gitlab.com/org/proj/-/merge_requests/1",
    )
    assert result["mr_url"] == "https://gitlab.com/org/proj/-/merge_requests/1"
    assert result["mr_iid"] == 1
    assert result["error"] is None
    assert isinstance(result["comments"], list)


def test_review_single_mr_captures_error():
    mock_client = MagicMock()
    mock_client.get_mr_diff.side_effect = Exception("API down")
    config = {"gitlab_url": "https://gitlab.com", "gitlab_pat": "fake", "batch_size": 30}

    from sensei.cli import _review_single_mr
    result = _review_single_mr(
        client=mock_client, config=config,
        project_path="org/proj", mr_iid=1,
        mr_url="https://gitlab.com/org/proj/-/merge_requests/1",
    )
    assert result["error"] is not None
    assert "API down" in result["error"]


def test_post_review_results_posts_musts_inline():
    mock_client = MagicMock()
    comments = [{"file": "src/app.tsx", "line": 10, "confidence": 95, "type": "must", "body": "Bug here"}]
    diff_lines_map = {"src/app.tsx": {10}}
    mr_data = {"base_sha": "a", "head_sha": "b", "start_sha": "c", "files": []}

    from sensei.cli import _post_review_results
    inline_posted, nits_posted, test_posted, skipped = _post_review_results(
        client=mock_client, project_path="org/proj", mr_iid=1,
        mr_data=mr_data, comments=comments, test_summary=None,
        diff_lines_map=diff_lines_map, existing=set(),
    )
    assert inline_posted >= 1
    mock_client.post_inline_comment.assert_called_once()
