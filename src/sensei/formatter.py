from itertools import groupby
from operator import itemgetter
from typing import Optional


def format_review(comments: list, test_summary: Optional[str] = None) -> str:
    """Format comments for terminal display, grouped by type."""
    if not comments and not test_summary:
        return "No comments - LGTM!"

    musts = [c for c in comments if c.get("type") not in ("nit", "test")]
    nits = [c for c in comments if c.get("type") == "nit"]

    lines = []

    if musts:
        lines.append("\nMUST FIX (posted inline):")
        sorted_musts = sorted(musts, key=itemgetter("file"))
        for file_path, file_comments in groupby(sorted_musts, key=itemgetter("file")):
            lines.append(f"\n  {file_path}")
            lines.append("  " + "-" * min(len(file_path), 60))
            for c in sorted(file_comments, key=itemgetter("line")):
                lines.append(f"\n  L{c['line']}:")
                for body_line in c["body"].splitlines():
                    lines.append(f"    {body_line}")

    if nits:
        lines.append("\nNITS (posted as summary):")
        sorted_nits = sorted(nits, key=itemgetter("file"))
        for file_path, file_comments in groupby(sorted_nits, key=itemgetter("file")):
            lines.append(f"\n  {file_path}")
            lines.append("  " + "-" * min(len(file_path), 60))
            for c in sorted(file_comments, key=itemgetter("line")):
                lines.append(f"\n  L{c['line']}:")
                for body_line in c["body"].splitlines():
                    lines.append(f"    {body_line}")

    if test_summary:
        lines.append("\n" + test_summary)

    file_count = _count_files(comments)
    if test_summary:
        lines.append(f"\n{len(comments)} comment(s) across {file_count} file(s) + test coverage summary")
    else:
        lines.append(f"\n{len(comments)} comment(s) across {file_count} file(s)")
    return "\n".join(lines)


def _count_files(comments: list) -> int:
    return len(set(c["file"] for c in comments))


def format_nits_summary(nit_comments: list) -> str:
    """Format all nits into one markdown summary comment."""
    if not nit_comments:
        return ""

    lines = ["## Nits"]
    sorted_nits = sorted(nit_comments, key=itemgetter("file"))
    for file_path, file_comments in groupby(sorted_nits, key=itemgetter("file")):
        lines.append(f"\n### `{file_path}`")
        for c in sorted(file_comments, key=itemgetter("line")):
            lines.append(f"**L{c['line']}:** {c['body']}")

    return "\n".join(lines)


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
