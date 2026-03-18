from setu_review.reviewer import build_file_review_prompt, parse_json_review, parse_review_output, load_project_rules_from_repo, _has_error_handling


def test_build_file_review_prompt_includes_diff():
    prompt = build_file_review_prompt(
        file_path="src/auth.py",
        diff="+ def login():\n+     pass",
        file_content="def login():\n    pass",
        style_profile="Priorities: readability",
        project_rules="Use type hints everywhere",
        mr_context="MR: Add login endpoint",
    )
    assert "src/auth.py" in prompt
    assert "def login" in prompt
    assert "readability" in prompt
    assert "type hints" in prompt
    assert "Confidence Scoring" in prompt
    assert "Silent Failures" in prompt


def test_parse_json_review_extracts_comments():
    raw = '''[
        {
            "line": 12,
            "confidence": 92,
            "severity": "critical",
            "category": "bug",
            "observation": "Missing null check for user parameter",
            "rule": "Do not mutate input parameters",
            "suggestion": "Add guard clause: if (!user) return null;"
        },
        {
            "line": 45,
            "confidence": 85,
            "severity": "important",
            "category": "style",
            "observation": "Nested if/else adds complexity",
            "rule": "Prefer early returns over else",
            "suggestion": "Use early return for the falsy case"
        }
    ]'''
    comments = parse_json_review(raw, "src/auth.py")
    assert len(comments) == 2
    assert comments[0]["line"] == 12
    assert comments[0]["confidence"] == 92
    assert comments[0]["severity"] == "critical"
    assert "null check" in comments[0]["body"]
    assert 'Per our standards' in comments[0]["body"]
    assert "Suggestion:" in comments[0]["body"]


def test_parse_json_review_filters_low_confidence():
    raw = '''[
        {"line": 10, "confidence": 75, "severity": "important", "category": "style",
         "observation": "Minor nitpick", "rule": "n/a", "suggestion": "n/a"},
        {"line": 20, "confidence": 90, "severity": "critical", "category": "bug",
         "observation": "Real bug", "rule": "No any", "suggestion": "Fix it"}
    ]'''
    comments = parse_json_review(raw, "src/foo.py")
    assert len(comments) == 1
    assert comments[0]["line"] == 20


def test_parse_json_review_empty_array():
    comments = parse_json_review("[]", "src/auth.py")
    assert len(comments) == 0


def test_parse_json_review_handles_markdown_wrapped():
    raw = '''```json
    [{"line": 5, "confidence": 85, "severity": "important", "category": "naming",
      "observation": "Bad name", "rule": "Use clear names", "suggestion": "Rename"}]
    ```'''
    comments = parse_json_review(raw, "src/foo.py")
    assert len(comments) == 1


def test_parse_review_output_lgtm():
    raw = "LGTM"
    comments = parse_review_output(raw, "src/auth.py")
    assert len(comments) == 0


def test_has_error_handling_detects_patterns():
    assert _has_error_handling("try { foo() } catch (e) {}")
    assert _has_error_handling("promise.catch(err => {})")
    assert _has_error_handling("user?.name")
    assert _has_error_handling("value ?? fallback")
    assert not _has_error_handling("const x = 1 + 2;")


def test_load_project_rules_from_repo_returns_string():
    result = load_project_rules_from_repo(None, "fake/project", "main")
    assert isinstance(result, str)
