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
    return f"""You are a senior code reviewer. Review ONLY the changed lines in this diff.

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

For each issue found, output a comment block in this exact format:

---
L<line_number> [<category>]
<observation about what the code does and what the issue is>
Per our standards: "<quote the specific rule being violated>"
Suggestion: <concrete actionable fix>
---

Categories: bug, style, naming, performance, security, suggestion, question

Rules for writing comments:
- Be specific. Reference actual variable names, function names, and values.
- Always cite which project rule or standard applies using "Per our standards:" with a direct quote.
- The suggestion must be concrete and actionable — not vague advice.
- If the change looks good, output only: LGTM
- Do not output anything else outside the --- delimiters."""


def parse_review_output(raw: str, file_path: str) -> list:
    """Parse Claude's review output into structured comments."""
    comments = []
    raw = raw.strip()

    if raw == "LGTM":
        return comments

    # Split on --- delimiters
    blocks = re.split(r'^---\s*$', raw, flags=re.MULTILINE)

    for block in blocks:
        block = block.strip()
        if not block:
            continue

        # First line should be L<number> [category]
        lines = block.splitlines()
        header_match = re.match(r'L(\d+)\s*\[(\w+)\]', lines[0].strip())
        if header_match:
            line_num = int(header_match.group(1))
            category = header_match.group(2)
            body = "\n".join(lines[1:]).strip()
            comments.append({
                "file": file_path,
                "line": line_num,
                "category": category,
                "body": body,
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
                 "body": f"Review failed: exit={result.returncode} stderr={result.stderr[:500]} stdout={result.stdout[:500]}"}]

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
