import re
from urllib.parse import urlparse
import gitlab


def parse_mr_url(url: str) -> tuple:
    """Extract project path and MR IID from a GitLab MR URL."""
    url = url.rstrip("/")
    parsed = urlparse(url)
    match = re.match(
        r"^/(.+?)/-/merge_requests/(\d+)",
        parsed.path,
    )
    if not match:
        raise ValueError(f"Invalid MR URL: {url}")
    return match.group(1), int(match.group(2))


class GitLabClient:
    def __init__(self, url: str, pat: str):
        self.gl = gitlab.Gitlab(url, private_token=pat)
        self.gl.auth()

    def get_mr_diff(self, project_path: str, mr_iid: int) -> dict:
        """Fetch MR metadata and per-file diffs."""
        project = self.gl.projects.get(project_path)
        mr = project.mergerequests.get(mr_iid)
        changes = mr.changes()

        # Get diff refs for inline commenting
        diff_refs = changes.get("diff_refs", {}) or {}

        return {
            "title": mr.title,
            "description": mr.description or "",
            "source_branch": mr.source_branch,
            "target_branch": mr.target_branch,
            "author": mr.author["username"],
            "web_url": mr.web_url,
            "base_sha": diff_refs.get("base_sha", ""),
            "head_sha": diff_refs.get("head_sha", ""),
            "start_sha": diff_refs.get("start_sha", ""),
            "files": [
                {
                    "old_path": c["old_path"],
                    "new_path": c["new_path"],
                    "diff": c["diff"],
                    "new_file": c["new_file"],
                    "deleted_file": c["deleted_file"],
                    "renamed_file": c["renamed_file"],
                }
                for c in changes["changes"]
            ],
        }

    def get_file_content(self, project_path: str, file_path: str, ref: str) -> str:
        """Fetch full file content at a given ref."""
        project = self.gl.projects.get(project_path)
        try:
            f = project.files.get(file_path=file_path, ref=ref)
            return f.decode().decode("utf-8")
        except gitlab.exceptions.GitlabGetError:
            return ""

    def post_mr_comment(
        self, project_path: str, mr_iid: int, body: str
    ) -> None:
        """Post a general comment on an MR."""
        project = self.gl.projects.get(project_path)
        mr = project.mergerequests.get(mr_iid)
        mr.notes.create({"body": body})

    def post_inline_comment(
        self,
        project_path: str,
        mr_iid: int,
        file_path: str,
        new_line: int,
        body: str,
        base_sha: str,
        head_sha: str,
        start_sha: str,
    ) -> None:
        """Post an inline discussion on a specific line."""
        project = self.gl.projects.get(project_path)
        mr = project.mergerequests.get(mr_iid)
        mr.discussions.create({
            "body": body,
            "position": {
                "base_sha": base_sha,
                "head_sha": head_sha,
                "start_sha": start_sha,
                "position_type": "text",
                "new_path": file_path,
                "new_line": new_line,
            },
        })
