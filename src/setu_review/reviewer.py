import re
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from setu_review.config import CONFIG_DIR


def build_file_review_prompt(
    file_path: str,
    diff: str,
    file_content: str,
    style_profile: str,
    project_rules: str,
    mr_context: str,
) -> str:
    return f"""You are a code reviewer. Review ONLY the changed lines in this diff.

## Your Review Style
{style_profile}

## Project Rules
{project_rules}

## MR Context
{mr_context}

## File: {file_path}

### Full file content (for context):
```
{file_content}
```

### Diff (review these changes):
```diff
{diff}
```

## Output Format
Output ONLY review comments, one per line, in this exact format:
L<line_number>: [<category>] <comment>

Categories: bug, style, naming, performance, security, suggestion, question

If the changes look good, output:
LGTM

Do not output anything else."""


def parse_review_output(raw: str, file_path: str) -> list:
    """Parse Claude's review output into structured comments."""
    comments = []
    for line in raw.strip().splitlines():
        line = line.strip()
        if line == "LGTM" or not line:
            continue
        match = re.match(r"L(\d+):\s*\[(\w+)\]\s*(.+)", line)
        if match:
            comments.append({
                "file": file_path,
                "line": int(match.group(1)),
                "category": match.group(2),
                "body": match.group(3),
            })
    return comments


def review_file(
    file_path: str,
    diff: str,
    file_content: str,
    style_profile: str,
    project_rules: str,
    mr_context: str,
) -> list:
    """Review a single file using claude CLI."""
    prompt = build_file_review_prompt(
        file_path, diff, file_content, style_profile, project_rules, mr_context
    )
    result = subprocess.run(
        ["claude", "-p", "--output-format", "text"],
        input=prompt,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        return [{"file": file_path, "line": 0, "category": "error",
                 "body": f"Review failed: {result.stderr[:200]}"}]

    return parse_review_output(result.stdout, file_path)


def review_mr_files(
    files: list,
    file_contents: dict,
    style_profile: str,
    project_rules: str,
    mr_context: str,
    batch_size: int = 30,
) -> list:
    """Review all MR files in parallel batches."""
    all_comments = []

    for batch_start in range(0, len(files), batch_size):
        batch = files[batch_start : batch_start + batch_size]
        print(f"  Reviewing batch {batch_start // batch_size + 1} "
              f"({len(batch)} files)...")

        with ThreadPoolExecutor(max_workers=min(len(batch), 8)) as executor:
            futures = {}
            for f in batch:
                path = f["new_path"]
                if f["deleted_file"]:
                    continue
                future = executor.submit(
                    review_file,
                    file_path=path,
                    diff=f["diff"],
                    file_content=file_contents.get(path, ""),
                    style_profile=style_profile,
                    project_rules=project_rules,
                    mr_context=mr_context,
                )
                futures[future] = path

            for future in as_completed(futures):
                path = futures[future]
                try:
                    comments = future.result()
                    all_comments.extend(comments)
                    status = "LGTM" if not comments else f"{len(comments)} comments"
                    print(f"    {path}: {status}")
                except Exception as e:
                    all_comments.append({
                        "file": path, "line": 0,
                        "category": "error", "body": str(e),
                    })

    return all_comments


def load_style_profile() -> str:
    path = CONFIG_DIR / "style-profile.md"
    if path.exists():
        return path.read_text()
    return "No style profile found. Review using general best practices."


def load_project_rules(project_path: str) -> str:
    """Try to load project-specific rules from ~/.setu-review/rules/."""
    safe_name = project_path.replace("/", "_")
    rules_file = CONFIG_DIR / "rules" / f"{safe_name}.md"
    if rules_file.exists():
        return rules_file.read_text()
    return "No project-specific rules found."


def load_project_rules_from_repo(client, project_path: str, ref: str) -> str:
    """Fetch CLAUDE.md and other rule files from the repo."""
    if client is None:
        return ""

    rules = []
    rule_files = ["CLAUDE.md", ".claude/rules.md", "CODING_PRINCIPLES.md"]

    for rule_file in rule_files:
        content = client.get_file_content(project_path, rule_file, ref)
        if content:
            rules.append(f"# From {rule_file}\n\n{content}")

    return "\n\n---\n\n".join(rules) if rules else ""
