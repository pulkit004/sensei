from setu_review.formatter import format_review, format_for_gitlab


def test_format_review_groups_by_file():
    comments = [
        {"file": "src/a.py", "line": 10, "category": "bug", "body": "Missing check"},
        {"file": "src/a.py", "line": 20, "category": "style", "body": "Use const"},
        {"file": "src/b.py", "line": 5, "category": "naming", "body": "Rename var"},
    ]
    output = format_review(comments)
    assert "src/a.py" in output
    assert "src/b.py" in output
    assert "L10" in output


def test_format_review_empty():
    output = format_review([])
    assert "LGTM" in output or "No comments" in output


def test_format_for_gitlab_produces_markdown():
    comments = [
        {"file": "src/a.py", "line": 10, "category": "bug", "body": "Missing check"},
    ]
    md = format_for_gitlab(comments)
    assert "src/a.py" in md
    assert "bug" in md.lower()
