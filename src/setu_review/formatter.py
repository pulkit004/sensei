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
        lines.append("  " + "-" * min(len(file_path), 60))
        for c in sorted(file_comments, key=itemgetter("line")):
            lines.append(f"\n  L{c['line']}:")
            for body_line in c["body"].splitlines():
                lines.append(f"    {body_line}")

    lines.append(f"\n{len(comments)} comment(s) across {_count_files(comments)} file(s)")
    return "\n".join(lines)


def _count_files(comments: list) -> int:
    return len(set(c["file"] for c in comments))


def format_for_gitlab(comments: list) -> str:
    """Format as a single markdown comment for GitLab."""
    if not comments:
        return "LGTM - no issues found."

    lines = []
    sorted_comments = sorted(comments, key=itemgetter("file"))
    for file_path, file_comments in groupby(sorted_comments, key=itemgetter("file")):
        lines.append(f"### `{file_path}`\n")
        for c in sorted(file_comments, key=itemgetter("line")):
            lines.append(f"**L{c['line']}**\n\n{c['body']}\n\n---\n")

    return "\n".join(lines)


def format_inline_comment(comment: dict) -> str:
    """Format a single comment for inline GitLab posting."""
    return comment["body"]
