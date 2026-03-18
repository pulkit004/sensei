from itertools import groupby
from operator import itemgetter


def format_review(comments: list) -> str:
    """Format comments for terminal display."""
    if not comments:
        return "No comments - LGTM!"

    lines = []
    sorted_comments = sorted(comments, key=itemgetter("file"))
    for file_path, file_comments in groupby(sorted_comments, key=itemgetter("file")):
        lines.append(f"\n  {file_path}")
        lines.append("  " + "-" * len(file_path))
        for c in sorted(file_comments, key=itemgetter("line")):
            lines.append(f"  L{c['line']} [{c['category']}]")
            for body_line in c["body"].splitlines():
                lines.append(f"    {body_line}")
            lines.append("")

    lines.append(f"Total: {len(comments)} comment(s)")
    return "\n".join(lines)


def format_for_gitlab(comments: list) -> str:
    """Format as a single markdown comment for GitLab."""
    if not comments:
        return "LGTM - no issues found."

    lines = ["## Code Review\n"]
    sorted_comments = sorted(comments, key=itemgetter("file"))
    for file_path, file_comments in groupby(sorted_comments, key=itemgetter("file")):
        lines.append(f"### `{file_path}`\n")
        for c in sorted(file_comments, key=itemgetter("line")):
            lines.append(f"**L{c['line']}** [{c['category']}]\n")
            lines.append(f"{c['body']}\n")
        lines.append("---\n")

    return "\n".join(lines)


def format_inline_comment(comment: dict) -> str:
    """Format a single comment for inline GitLab posting."""
    return f"**Code Review** [{comment['category']}]\n\n{comment['body']}"
