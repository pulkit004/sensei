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
    raw = """L12: [bug] Missing null check for user parameter
L45: [style] Prefer early return over nested if
L89: [naming] Variable 'x' should be descriptive"""
    comments = parse_review_output(raw, "src/auth.py")
    assert len(comments) == 3
    assert comments[0]["line"] == 12
    assert comments[0]["category"] == "bug"
    assert "null check" in comments[0]["body"]
    assert comments[0]["file"] == "src/auth.py"


def test_parse_review_output_lgtm():
    raw = "LGTM"
    comments = parse_review_output(raw, "src/auth.py")
    assert len(comments) == 0


def test_load_project_rules_from_repo_returns_string():
    result = load_project_rules_from_repo(None, "fake/project", "main")
    assert isinstance(result, str)
