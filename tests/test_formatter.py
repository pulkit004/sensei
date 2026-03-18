from setu_review.formatter import format_review, format_for_gitlab, format_inline_comment


def test_format_review_groups_by_severity():
    comments = [
        {"file": "src/a.py", "line": 10, "confidence": 95, "severity": "critical", "category": "bug", "body": "Missing check"},
        {"file": "src/a.py", "line": 20, "confidence": 82, "severity": "important", "category": "style", "body": "Use const"},
        {"file": "src/b.py", "line": 5, "confidence": 88, "severity": "important", "category": "naming", "body": "Rename var"},
    ]
    output = format_review(comments)
    assert "CRITICAL" in output
    assert "IMPORTANT" in output
    assert "1 critical" in output
    assert "2 important" in output


def test_format_review_empty():
    output = format_review([])
    assert "LGTM" in output or "No comments" in output


def test_format_for_gitlab_produces_markdown():
    comments = [
        {"file": "src/a.py", "line": 10, "confidence": 92, "severity": "critical", "category": "bug", "body": "Missing check"},
    ]
    md = format_for_gitlab(comments)
    assert "src/a.py" in md
    assert "Critical" in md


def test_format_inline_comment():
    comment = {
        "severity": "critical",
        "category": "bug",
        "body": "Missing null check.\nPer our standards: \"Validate inputs.\"\nSuggestion: Add guard clause.",
    }
    result = format_inline_comment(comment)
    assert "Code Review" in result
    assert "CRITICAL" in result
    assert "bug" in result
    assert "Per our standards" in result
