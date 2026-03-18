from setu_review.formatter import format_review, format_for_gitlab, format_inline_comment


def test_format_review_groups_by_file():
    comments = [
        {"file": "src/a.py", "line": 10, "confidence": 95, "body": "Code Review: Missing null check."},
        {"file": "src/a.py", "line": 20, "confidence": 82, "body": "Code Review: Use const."},
        {"file": "src/b.py", "line": 5, "confidence": 88, "body": "Code Review: Rename var."},
    ]
    output = format_review(comments)
    assert "src/a.py" in output
    assert "src/b.py" in output
    assert "3 comment(s)" in output
    assert "2 file(s)" in output


def test_format_review_empty():
    output = format_review([])
    assert "LGTM" in output


def test_format_for_gitlab_produces_markdown():
    comments = [
        {"file": "src/a.py", "line": 10, "confidence": 92, "body": "Code Review: Missing check."},
    ]
    md = format_for_gitlab(comments)
    assert "src/a.py" in md
    assert "Missing check" in md


def test_format_inline_comment_is_just_the_body():
    comment = {"body": "Code Review: Missing null check.\nPer our standards: \"Validate inputs.\"\nSuggestion: Add guard clause."}
    result = format_inline_comment(comment)
    assert result == comment["body"]
    assert "Code Review:" in result
