from sensei.formatter import format_review, format_for_gitlab, format_inline_comment, format_nits_summary


def test_format_review_groups_by_type():
    comments = [
        {"file": "src/a.py", "line": 10, "confidence": 95, "type": "must", "body": "Code Review: Missing null check."},
        {"file": "src/a.py", "line": 20, "confidence": 82, "type": "nit", "body": "Code Review: Use const."},
        {"file": "src/b.py", "line": 5, "confidence": 88, "type": "nit", "body": "Code Review: Rename var."},
    ]
    output = format_review(comments)
    assert "MUST FIX (posted inline):" in output
    assert "NITS (posted as summary):" in output
    assert "src/a.py" in output
    assert "src/b.py" in output
    assert "3 comment(s)" in output
    assert "2 file(s)" in output


def test_format_review_only_musts():
    comments = [
        {"file": "src/a.py", "line": 10, "confidence": 95, "type": "must", "body": "Code Review: Bug."},
    ]
    output = format_review(comments)
    assert "MUST FIX" in output
    assert "NITS" not in output


def test_format_review_only_nits():
    comments = [
        {"file": "src/a.py", "line": 10, "confidence": 82, "type": "nit", "body": "Code Review: Style."},
    ]
    output = format_review(comments)
    assert "NITS" in output
    assert "MUST FIX" not in output


def test_format_review_empty():
    output = format_review([])
    assert "LGTM" in output


def test_format_nits_summary():
    nits = [
        {"file": "src/a.py", "line": 10, "confidence": 82, "type": "nit", "body": "Code Review: Use const instead of let."},
        {"file": "src/a.py", "line": 30, "confidence": 85, "type": "nit", "body": "Code Review: Rename variable."},
        {"file": "src/b.py", "line": 20, "confidence": 83, "type": "nit", "body": "Code Review: Add docstring."},
    ]
    output = format_nits_summary(nits)
    assert "## Nits" in output
    assert "### `src/a.py`" in output
    assert "### `src/b.py`" in output
    assert "**L10:**" in output
    assert "**L30:**" in output
    assert "**L20:**" in output
    assert "Use const" in output


def test_format_nits_summary_empty():
    output = format_nits_summary([])
    assert output == ""


def test_format_for_gitlab_produces_markdown():
    comments = [
        {"file": "src/a.py", "line": 10, "confidence": 92, "body": "Code Review: Missing check."},
    ]
    md = format_for_gitlab(comments)
    assert "src/a.py" in md
    assert "Missing check" in md


def test_format_review_with_test_summary():
    comments = [
        {"file": "src/a.py", "line": 10, "confidence": 95, "type": "must", "body": "Code Review: Bug."},
    ]
    test_summary = "## Test Coverage Summary\n\nSome areas need tests."
    output = format_review(comments, test_summary)
    assert "MUST FIX" in output
    assert "## Test Coverage Summary" in output
    assert "1 comment(s)" in output
    assert "test coverage summary" in output


def test_format_review_excludes_test_type_from_sections():
    """Test type comments should not appear in MUST FIX or NITS sections."""
    comments = [
        {"file": "src/a.py", "line": 10, "confidence": 95, "type": "must", "body": "Code Review: Bug."},
        {"file": "src/a.py", "line": 20, "confidence": 92, "type": "test", "body": "Needs tests"},
    ]
    output = format_review(comments)
    # test type shouldn't appear in MUST FIX or NITS
    assert "Needs tests" not in output


def test_format_inline_comment_is_just_the_body():
    comment = {"body": "Code Review: Missing null check.\nSuggestion: Add guard clause."}
    result = format_inline_comment(comment)
    assert result == comment["body"]
    assert "Code Review:" in result


def test_format_batch_progress():
    from sensei.formatter import format_batch_progress
    line = format_batch_progress(47, "building-bridges-frontend", "reviewing 3/5 files...")
    assert "!47" in line
    assert "building-bridges-frontend" in line
    assert "reviewing 3/5 files..." in line


def test_format_batch_progress_short_project():
    from sensei.formatter import format_batch_progress
    line = format_batch_progress(126, "brokentusk/facade/docs-mdx", "done — 4 comments")
    assert "!126" in line
    assert "docs-mdx" in line
    assert "done — 4 comments" in line
