from setu_review.reviewer import build_file_review_prompt, parse_review_output, load_project_rules_from_repo


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


def test_parse_review_output_extracts_comments():
    raw = """---
L12 [bug]
The `user` parameter is not checked for null before accessing `.name`.
Per our standards: "Do not mutate input parameters."
Suggestion: Add a guard clause: `if (!user) return null;`
---
L45 [style]
Nested if/else block adds unnecessary indentation.
Per our standards: "Prefer early returns over else."
Suggestion: Use an early return for the falsy case.
---"""
    comments = parse_review_output(raw, "src/auth.py")
    assert len(comments) == 2
    assert comments[0]["line"] == 12
    assert comments[0]["category"] == "bug"
    assert "null" in comments[0]["body"]
    assert comments[0]["file"] == "src/auth.py"
    assert "Per our standards" in comments[1]["body"]


def test_parse_review_output_lgtm():
    raw = "LGTM"
    comments = parse_review_output(raw, "src/auth.py")
    assert len(comments) == 0


def test_load_project_rules_from_repo_returns_string():
    result = load_project_rules_from_repo(None, "fake/project", "main")
    assert isinstance(result, str)
