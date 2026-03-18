from itertools import groupby
from operator import itemgetter


def format_review(comments: list) -> str:
    """Format comments for terminal display."""
    if not comments:
        return "No comments - LGTM!"

    # Group by severity
    critical = [c for c in comments if c.get("severity") == "critical"]
    important = [c for c in comments if c.get("severity") != "critical"]

    lines = []

    if critical:
        lines.append("\n  CRITICAL (confidence 90-100)")
        lines.append("  " + "=" * 40)
        _format_comment_group(critical, lines)

    if important:
        lines.append("\n  IMPORTANT (confidence 80-89)")
        lines.append("  " + "=" * 40)
        _format_comment_group(important, lines)

    lines.append(f"\nTotal: {len(comments)} comment(s) ({len(critical)} critical, {len(important)} important)")
    return "\n".join(lines)


def _format_comment_group(comments: list, lines: list):
    """Format a group of comments by file."""
    sorted_comments = sorted(comments, key=itemgetter("file"))
    for file_path, file_comments in groupby(sorted_comments, key=itemgetter("file")):
        lines.append(f"\n  {file_path}")
        lines.append("  " + "-" * len(file_path))
        for c in sorted(file_comments, key=itemgetter("line")):
            conf = c.get("confidence", "?")
            lines.append(f"  L{c['line']} [{c['category']}] (confidence: {conf})")
            for body_line in c["body"].splitlines():
                lines.append(f"    {body_line}")
            lines.append("")


def format_for_gitlab(comments: list) -> str:
    """Format as a single markdown comment for GitLab."""
    if not comments:
        return "LGTM - no issues found."

    lines = ["## Code Review\n"]

    critical = [c for c in comments if c.get("severity") == "critical"]
    important = [c for c in comments if c.get("severity") != "critical"]

    if critical:
        lines.append("### Critical Issues\n")
        _format_gitlab_group(critical, lines)

    if important:
        lines.append("### Important Issues\n")
        _format_gitlab_group(important, lines)

    return "\n".join(lines)


def _format_gitlab_group(comments: list, lines: list):
    """Format a group for GitLab markdown."""
    sorted_comments = sorted(comments, key=itemgetter("file"))
    for file_path, file_comments in groupby(sorted_comments, key=itemgetter("file")):
        lines.append(f"#### `{file_path}`\n")
        for c in sorted(file_comments, key=itemgetter("line")):
            lines.append(f"**L{c['line']}** [{c['category']}]\n")
            lines.append(f"{c['body']}\n")
        lines.append("---\n")


def format_inline_comment(comment: dict) -> str:
    """Format a single comment for inline GitLab posting."""
    severity = comment.get("severity", "important").upper()
    return f"**Code Review** [{severity}] [{comment['category']}]\n\n{comment['body']}"
