from itertools import groupby
from operator import itemgetter

CATEGORY_EMOJI = {
    "bug": "\U0001f41b",
    "style": "\U0001f3a8",
    "naming": "\U0001f4db",
    "performance": "\u26a1",
    "security": "\U0001f512",
    "suggestion": "\U0001f4a1",
    "question": "\u2753",
    "error": "\u274c",
}


def format_review(comments: list) -> str:
    """Format comments for terminal display."""
    if not comments:
        return "\u2705 No comments \u2014 LGTM!"

    lines = []
    sorted_comments = sorted(comments, key=itemgetter("file"))
    for file_path, file_comments in groupby(sorted_comments, key=itemgetter("file")):
        lines.append(f"\n\U0001f4c1 {file_path}")
        for c in sorted(file_comments, key=itemgetter("line")):
            emoji = CATEGORY_EMOJI.get(c["category"], "\U0001f4dd")
            lines.append(f"  L{c['line']}: {emoji} [{c['category']}] {c['body']}")

    lines.append(f"\nTotal: {len(comments)} comment(s)")
    return "\n".join(lines)


def format_for_gitlab(comments: list) -> str:
    """Format comments as a single markdown comment for GitLab."""
    if not comments:
        return "\u2705 LGTM \u2014 no issues found."

    lines = ["## Code Review\n"]
    sorted_comments = sorted(comments, key=itemgetter("file"))
    for file_path, file_comments in groupby(sorted_comments, key=itemgetter("file")):
        lines.append(f"### `{file_path}`\n")
        for c in sorted(file_comments, key=itemgetter("line")):
            lines.append(f"- **L{c['line']}** [{c['category']}]: {c['body']}")
        lines.append("")

    return "\n".join(lines)
