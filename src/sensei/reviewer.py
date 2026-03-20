import json
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from sensei.config import CONFIG_DIR


def build_file_review_prompt(
    file_path: str,
    diff: str,
    file_content: str,
    style_profile: str,
    project_rules: str,
    mr_context: str,
) -> str:
    return f"""You are a thoughtful senior engineer reviewing a teammate's code. Write like a human — direct, specific, helpful. No corporate tone, no robotic structure, no filler.

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

## What to look for
- Bugs, type safety issues, implicit `any`
- Silent failures, swallowed errors, fallbacks that hide problems
- Naming inconsistencies, missing conventions
- Security issues, environment misconfigs
- Architecture violations (cross-layer leakage, duplication across packages)

## Test coverage gaps
If the diff adds or changes logic that has no corresponding test, emit a SEPARATE entry with `"type": "test"`. Do NOT write a full comment — just state what needs testing in one line.
Example: `{{"line": 42, "confidence": 92, "type": "test", "comment": "New `redirectToOnboarding` logic needs tests for different productType/accountId combos"}}`
Do NOT emit per-file "missing tests" comments as "must" or "nit" — use "test" type ONLY. These will be consolidated into a single test summary.

## Writing style for comments

Write each comment like a thoughtful human colleague — concise, scannable, empathetic. Keep it SHORT.

EXAMPLE:

"Code Review: `user` param is not null-checked before `.name` access.

• Crashes at runtime if caller passes undefined

Suggestion: Add a guard clause: `if (!user) return null;`"

RULES:
1. Start with "Code Review:" — ONE short sentence, max 15 words. Be specific (use actual names, values).
2. 1-2 bullet points (•) max for the specific issues — one line each.
3. End with "Suggestion:" — one concrete, actionable sentence.
4. Only flag issues you're genuinely confident about (>= 80%).
5. Keep entire comment to 4-6 lines. If you need more than 2 bullets, you're overexplaining.

## Output Format

Return a valid JSON array. Each element:
- "line": integer (line number in the new file)
- "confidence": integer (80-100, used internally — not shown in comment)
- "type": "must", "nit", or "test" — "must" for confidence >= 90 (bugs, security, rule violations), "nit" for confidence 80-89 (naming, style, suggestions), "test" for missing test coverage (these get consolidated into one summary, not posted inline)
- "comment": string (the full human-readable comment as described above; for "test" type, just a one-line description of what needs testing)

If the changes look good, return: []

Return ONLY the JSON array, nothing else."""


def build_silent_failure_prompt(
    file_path: str,
    diff: str,
    file_content: str,
    project_rules: str,
) -> str:
    return f"""You are reviewing error handling in a teammate's code. Look for places where errors are silently swallowed, users get no feedback, or fallbacks mask real problems.

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

## What to look for
- Empty catch blocks
- Catch blocks that only log and continue — user gets no feedback
- Returning null/undefined/default on error without logging
- Optional chaining (?.) silently skipping important operations
- Fallback values that mask underlying problems
- Missing error propagation — error should bubble up but doesn't
- Generic catch blocks catching all errors when only specific ones expected

## Writing style

RULES:
1. "Code Review:" — ONE short sentence, max 15 words. Be specific.
2. 1-2 bullet points (•) max — one line each.
3. "Suggestion:" — one concrete, actionable sentence.
4. Only flag issues >= 80% confidence.
5. Keep entire comment to 4-6 lines. If you need more than 2 bullets, you're overexplaining.

## Output Format

Return a valid JSON array. Each element:
- "line": integer
- "confidence": integer (80-100)
- "type": "must" or "nit" — "must" for confidence >= 90 (bugs, security, missing error handling), "nit" for confidence 80-89 (style, suggestions)
- "comment": string (the full human-readable comment)

If no issues found, return: []

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

        # Support both new format ("comment") and old format ("observation"/"rule"/"suggestion")
        if item.get("comment"):
            body = item["comment"]
        else:
            body_parts = []
            if item.get("observation"):
                body_parts.append(item["observation"])
            if item.get("rule"):
                body_parts.append(f'Per our standards: "{item["rule"]}"')
            if item.get("suggestion"):
                body_parts.append(f"Suggestion: {item['suggestion']}")
            body = "\n".join(body_parts)

        # Determine type: "test" preserved as-is, else "must" >= 90, "nit" 80-89
        raw_type = item.get("type", "")
        if raw_type == "test":
            comment_type = "test"
        else:
            comment_type = raw_type if raw_type in ("must", "nit") else ("must" if confidence >= 90 else "nit")

        comments.append({
            "file": file_path,
            "line": item.get("line", 0),
            "confidence": confidence,
            "type": comment_type,
            "body": body,
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
                                                "body": str(e),
                    })

    # Sort by confidence (highest first), then by file
    all_comments.sort(key=lambda c: (-c.get("confidence", 0), c.get("file", "")))

    return all_comments


def consolidate_test_comments(comments: list) -> tuple:
    """Separate test-gap comments from review comments and build a summary.

    Returns (review_comments, test_summary_comment_or_none).
    """
    review = [c for c in comments if c.get("type") != "test"]
    test_gaps = [c for c in comments if c.get("type") == "test"]

    if not test_gaps:
        return review, None

    # Group by file, deduplicate similar descriptions
    from itertools import groupby
    from operator import itemgetter

    sorted_gaps = sorted(test_gaps, key=itemgetter("file"))
    rows = []
    for file_path, file_comments in groupby(sorted_gaps, key=itemgetter("file")):
        for c in file_comments:
            rows.append((file_path, c.get("body", c.get("comment", ""))))

    # Deduplicate rows with near-identical descriptions (same file, same first 60 chars)
    seen = set()
    unique_rows = []
    for file_path, desc in rows:
        key = (file_path, desc[:60])
        if key not in seen:
            seen.add(key)
            unique_rows.append((file_path, desc))

    # Build markdown table
    lines = [
        "## Test Coverage Summary",
        "",
        "This MR adds/changes logic without corresponding tests. "
        "Target ~80% coverage for new code. Key areas needing tests:",
        "",
        "| Area | What to test |",
        "|---|---|",
    ]
    for file_path, desc in unique_rows:
        # Use short filename for readability
        short = file_path.rsplit("/", 1)[-1] if "/" in file_path else file_path
        lines.append(f"| `{short}` | {desc} |")

    lines.append("")
    lines.append(
        "If multiple files share the same pattern (e.g., identical prop wiring), "
        "one well-tested example + replication is fine — focus depth on unique logic."
    )

    return review, "\n".join(lines)


def load_style_profile() -> str:
    path = CONFIG_DIR / "style-profile.md"
    if path.exists():
        return path.read_text()
    return "No style profile found. Review using general best practices."


def load_project_rules(project_path: str) -> str:
    """Try to load project-specific rules from ~/.sensei/rules/."""
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
