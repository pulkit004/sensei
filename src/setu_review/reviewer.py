import json
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
    return f"""You are a senior code reviewer using a structured review methodology.
Review ONLY the changed lines in this diff. Be thorough but precise.

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

## Review Checklist

Evaluate the changes against each dimension:

1. **Code Quality**: Separation of concerns, error handling, type safety, DRY, edge cases
2. **Architecture**: Design decisions, scalability, cross-layer leakage
3. **Naming & Types**: Clear names, consistent conventions, type precision
4. **Error Handling & Silent Failures**:
   - Are there try-catch blocks that swallow errors?
   - Are there fallbacks that mask underlying problems?
   - Will the user get actionable feedback if something fails?
   - Are there empty catch blocks or catch-and-continue patterns?
5. **Testing**: Are corresponding tests included? Do they test behavior, not implementation?
6. **Security**: Input validation, sensitive data exposure
7. **Performance**: Unnecessary re-renders, expensive operations, missing memoization

## Confidence Scoring

For each issue you find, assign a confidence score (0-100):
- 90-100: Critical — explicit rule violation, definite bug, or security issue
- 80-89: Important — strong evidence of a real problem
- Below 80: DO NOT REPORT. Only report issues with confidence >= 80.

## Output Format

Return a valid JSON array. Each element must have these fields:
- "line": integer (line number in the new file)
- "confidence": integer (80-100)
- "severity": "critical" or "important"
- "category": one of "bug", "style", "naming", "performance", "security", "error-handling", "testing", "architecture"
- "observation": string (what the code does and what the issue is — be specific, reference actual names)
- "rule": string (the specific project rule or standard being violated — quote it directly)
- "suggestion": string (concrete, actionable fix)

If the changes look good and no issues have confidence >= 80, return:
[]

Return ONLY the JSON array, nothing else. No markdown, no explanation outside the JSON."""


def build_silent_failure_prompt(
    file_path: str,
    diff: str,
    file_content: str,
    project_rules: str,
) -> str:
    return f"""You are a silent failure hunter. Your job is to find error handling code that
silently fails, swallows errors, or gives users no feedback when things go wrong.

## Project Rules
{project_rules}

## File: {file_path}

### Full file content:
```
{file_content}
```

### Diff (focus on these changes):
```diff
{diff}
```

## What to Look For

1. **Empty catch blocks** — absolutely forbidden
2. **Catch blocks that only log and continue** — user gets no feedback
3. **Returning null/undefined/default on error without logging** — silent data loss
4. **Optional chaining (?.) silently skipping operations** — may hide real errors
5. **Fallback values that mask problems** — user doesn't know something went wrong
6. **Missing error propagation** — error should bubble up but doesn't
7. **Generic catch blocks** — catching all errors when only specific ones expected
8. **Retry logic that exhausts without informing user**

## Output Format

Return a valid JSON array. Each element:
- "line": integer
- "confidence": integer (80-100 only)
- "severity": "critical" or "important"
- "category": "error-handling"
- "observation": string (what error handling exists and why it's problematic)
- "rule": string (the standard being violated, e.g. "Never silently fail in production code")
- "suggestion": string (specific code change with example)

If no silent failure issues found, return:
[]

Return ONLY the JSON array."""


def parse_json_review(raw: str, file_path: str) -> list:
    """Parse JSON review output into structured comments."""
    raw = raw.strip()

    # Try to extract JSON array from the response
    # Sometimes Claude wraps it in markdown code blocks
    json_match = re.search(r'\[.*\]', raw, re.DOTALL)
    if not json_match:
        return []

    try:
        items = json.loads(json_match.group())
    except json.JSONDecodeError:
        return []

    comments = []
    for item in items:
        if not isinstance(item, dict):
            continue
        confidence = item.get("confidence", 0)
        if confidence < 80:
            continue

        body_parts = []
        if item.get("observation"):
            body_parts.append(item["observation"])
        if item.get("rule"):
            body_parts.append(f'Per our standards: "{item["rule"]}"')
        if item.get("suggestion"):
            body_parts.append(f"Suggestion: {item['suggestion']}")

        comments.append({
            "file": file_path,
            "line": item.get("line", 0),
            "confidence": confidence,
            "severity": item.get("severity", "important"),
            "category": item.get("category", "suggestion"),
            "body": "\n".join(body_parts),
        })

    return comments


# Keep backward compatibility for old format
def parse_review_output(raw: str, file_path: str) -> list:
    """Parse review output — tries JSON first, falls back to text format."""
    comments = parse_json_review(raw, file_path)
    if comments:
        return comments

    # Fallback: old text-based parsing
    if raw.strip() == "LGTM":
        return []

    blocks = re.split(r'^---\s*$', raw, flags=re.MULTILINE)
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        lines = block.splitlines()
        header_match = re.match(r'L(\d+)\s*\[(\w+)\]', lines[0].strip())
        if header_match:
            comments.append({
                "file": file_path,
                "line": int(header_match.group(1)),
                "confidence": 85,
                "severity": "important",
                "category": header_match.group(2),
                "body": "\n".join(lines[1:]).strip(),
            })

    return comments


def _has_error_handling(diff: str) -> bool:
    """Check if diff contains error handling patterns worth hunting."""
    patterns = [
        r'catch\s*\(',
        r'\.catch\(',
        r'try\s*\{',
        r'onError',
        r'\.error\(',
        r'fallback',
        r'\?\.',  # optional chaining
        r'\?\?',  # nullish coalescing
    ]
    for pattern in patterns:
        if re.search(pattern, diff):
            return True
    return False


def review_file(
    file_path: str,
    diff: str,
    file_content: str,
    style_profile: str,
    project_rules: str,
    mr_context: str,
) -> list:
    """Review a single file using claude CLI with superpowers methodology."""
    # Phase 1: Main code review
    prompt = build_file_review_prompt(
        file_path, diff, file_content, style_profile, project_rules, mr_context
    )
    result = subprocess.run(
        ["claude", "-p", "--output-format", "text"],
        input=prompt,
        capture_output=True,
        text=True,
        timeout=180,
    )
    if result.returncode != 0:
        return [{"file": file_path, "line": 0, "confidence": 100,
                 "severity": "critical", "category": "error",
                 "body": f"Review failed: exit={result.returncode} stderr={result.stderr[:500]}"}]

    comments = parse_json_review(result.stdout, file_path)

    # Phase 2: Silent failure hunting (only if diff has error handling patterns)
    if _has_error_handling(diff):
        sf_prompt = build_silent_failure_prompt(
            file_path, diff, file_content, project_rules
        )
        sf_result = subprocess.run(
            ["claude", "-p", "--output-format", "text"],
            input=sf_prompt,
            capture_output=True,
            text=True,
            timeout=180,
        )
        if sf_result.returncode == 0:
            sf_comments = parse_json_review(sf_result.stdout, file_path)
            # Deduplicate by line number
            existing_lines = {c["line"] for c in comments}
            for c in sf_comments:
                if c["line"] not in existing_lines:
                    comments.append(c)

    return comments


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
                        "file": path, "line": 0, "confidence": 100,
                        "severity": "critical", "category": "error",
                        "body": str(e),
                    })

    # Sort by severity (critical first) then confidence (highest first)
    severity_order = {"critical": 0, "important": 1}
    all_comments.sort(key=lambda c: (severity_order.get(c.get("severity", "important"), 1), -c.get("confidence", 0)))

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
