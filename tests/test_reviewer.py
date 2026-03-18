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
    assert "Code Review:" in prompt  # example format
    assert '"type"' in prompt  # new type field in output format


def test_parse_json_review_new_format():
    raw = '''[
        {
            "line": 12,
            "confidence": 92,
            "type": "must",
            "comment": "Code Review: The `user` parameter is not null-checked before accessing `.name`.\\n\\n\\u2022 Crashes at runtime if caller passes undefined\\n\\nSuggestion: Add a guard clause: `if (!user) return null;`"
        },
        {
            "line": 45,
            "confidence": 85,
            "type": "nit",
            "comment": "Code Review: Nested if/else adds unnecessary complexity.\\n\\n\\u2022 Prefer early returns over else\\n\\nSuggestion: Use an early return for the falsy case."
        }
    ]'''
    comments = parse_json_review(raw, "src/auth.py")
    assert len(comments) == 2
    assert comments[0]["line"] == 12
    assert comments[0]["confidence"] == 92
    assert comments[0]["type"] == "must"
    assert "Code Review:" in comments[0]["body"]
    assert comments[1]["type"] == "nit"


def test_parse_json_review_type_defaults_by_confidence():
    """When type field is missing, it defaults based on confidence threshold."""
    raw = '''[
        {"line": 10, "confidence": 95, "comment": "Code Review: Bug found."},
        {"line": 20, "confidence": 82, "comment": "Code Review: Style issue."}
    ]'''
    comments = parse_json_review(raw, "src/foo.py")
    assert len(comments) == 2
    assert comments[0]["type"] == "must"  # confidence 95 >= 90
    assert comments[1]["type"] == "nit"   # confidence 82 < 90


def test_parse_json_review_old_format_compat():
    raw = '''[
        {
            "line": 20,
            "confidence": 90,
            "observation": "Real bug",
            "rule": "No any",
            "suggestion": "Fix it"
        }
    ]'''
    comments = parse_json_review(raw, "src/foo.py")
    assert len(comments) == 1
    assert "Real bug" in comments[0]["body"]
    assert "Per our standards" in comments[0]["body"]
    assert comments[0]["type"] == "must"  # confidence 90 >= 90


def test_parse_json_review_filters_low_confidence():
    raw = '''[
        {"line": 10, "confidence": 75, "comment": "Minor nitpick"},
        {"line": 20, "confidence": 90, "comment": "Code Review: Real bug here."}
    ]'''
    comments = parse_json_review(raw, "src/foo.py")
    assert len(comments) == 1
    assert comments[0]["line"] == 20


def test_parse_json_review_empty_array():
    comments = parse_json_review("[]", "src/auth.py")
    assert len(comments) == 0


def test_parse_json_review_handles_markdown_wrapped():
    raw = '''```json
    [{"line": 5, "confidence": 85, "type": "nit", "comment": "Code Review: Bad name."}]
    ```'''
    comments = parse_json_review(raw, "src/foo.py")
    assert len(comments) == 1
    assert comments[0]["type"] == "nit"


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
