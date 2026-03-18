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
- Missing tests for new logic
- Security issues, environment misconfigs
- Architecture violations (cross-layer leakage, duplication across packages)

## Writing style for comments

Write each comment like a thoughtful human colleague — concise, scannable, empathetic. Follow this exact structure:

EXAMPLE:

"Code Review: This block adds ~36 lines of `!important` overrides using fragile `[class*="setu:..."]` attribute selectors.
While understandable as a migration shim, this is a maintenance risk:

• Attribute substring matching is brittle and can match unintended classes
• `!important` makes future CSS changes difficult to reason about

Suggestion: Add a `// TODO(BRIDGE-XXXX)`: Remove badge compatibility overrides once @setu/components Badge stabilizes comment with a tracking ticket so this doesn't become permanent technical debt."

RULES:
1. Start with "Code Review:" — one short sentence describing what you observe. Be specific (use actual names, values).
2. Acknowledge intent with "While understandable as [context], this is a [risk type]:" — show empathy, then name the risk.
3. Use bullet points (•) for the specific issues — keep each bullet to one line, scannable.
4. End with "Suggestion:" — one concrete, actionable fix in 1-2 sentences.
5. Keep the whole comment SHORT. If you can say it in 3 bullets, don't write 5.
6. Only flag issues you're genuinely confident about (>= 80%). Skip nitpicks.

## Output Format

Return a valid JSON array. Each element:
- "line": integer (line number in the new file)
- "confidence": integer (80-100, used internally — not shown in comment)
- "comment": string (the full human-readable comment as described above)

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

Use this structure:
1. "Code Review:" — short observation sentence
2. "While understandable as [context], this is a [risk]:" — acknowledge intent, name the risk
3. Bullet points (•) for specific issues — one line each, scannable
4. "Suggestion:" — concrete fix in 1-2 sentences

Keep it short. Only flag issues >= 80% confidence.

## Output Format

Return a valid JSON array. Each element:
- "line": integer
- "confidence": integer (80-100)
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

        comments.append({
            "file": file_path,
            "line": item.get("line", 0),
            "confidence": confidence,
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

    # Sort by severity (critical first) then confidence (highest first)
    # Sort by confidence (highest first), then by file
    all_comments.sort(key=lambda c: (-c.get("confidence", 0), c.get("file", "")))

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
