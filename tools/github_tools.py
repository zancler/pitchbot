import os
from datetime import datetime, timedelta, timezone
from github import Github, GithubException

_github_client = None


def get_github_client():
    global _github_client
    if _github_client is None:
        token = os.environ["GITHUB_TOKEN"]
        _github_client = Github(token)
    return _github_client


def get_repo():
    repo_name = os.environ["GITHUB_REPO"]  # e.g. "alice/my-project"
    return get_github_client().get_repo(repo_name)


def list_repo_files(directory: str = "") -> str:
    try:
        repo = get_repo()
        contents = repo.get_contents(directory)
        if not isinstance(contents, list):
            contents = [contents]
        lines = []
        for item in contents:
            icon = "📁" if item.type == "dir" else "📄"
            lines.append(f"{icon} {item.path}")
        return "\n".join(lines) if lines else "Empty directory."
    except GithubException as e:
        return f"GitHub error: {e.data.get('message', str(e))}"


def read_repo_file(path: str) -> str:
    try:
        repo = get_repo()
        file = repo.get_contents(path)
        content = file.decoded_content.decode("utf-8")
        if len(content) > 8000:
            content = content[:8000] + f"\n\n[... truncated — file is {len(content)} chars total]"
        return content
    except GithubException as e:
        return f"GitHub error: {e.data.get('message', str(e))}"


def get_github_issues(state: str = "open", limit: int = 10, label: str = None) -> str:
    try:
        repo = get_repo()
        kwargs = {"state": state}
        if label:
            kwargs["labels"] = [label]
        issues = list(repo.get_issues(**kwargs))[:limit]
        if not issues:
            return f"No {state} issues found."
        lines = []
        for issue in issues:
            assignee = issue.assignee.login if issue.assignee else "unassigned"
            labels = ", ".join(l.name for l in issue.labels) if issue.labels else ""
            label_str = f" [{labels}]" if labels else ""
            lines.append(f"#{issue.number} {issue.title}{label_str} — {assignee}")
        return "\n".join(lines)
    except GithubException as e:
        return f"GitHub error: {e.data.get('message', str(e))}"


def get_recent_commits(days: int = 7, branch: str = "main") -> str:
    try:
        repo = get_repo()
        since = datetime.now(timezone.utc) - timedelta(days=days)
        commits = list(repo.get_commits(sha=branch, since=since))
        if not commits:
            return f"No commits in the last {days} days on {branch}."
        lines = []
        for commit in commits[:20]:
            date = commit.commit.author.date.strftime("%b %d")
            author = commit.commit.author.name
            message = commit.commit.message.split("\n")[0]
            lines.append(f"{date} [{author}] {message}")
        return "\n".join(lines)
    except GithubException as e:
        return f"GitHub error: {e.data.get('message', str(e))}"


def get_open_prs(limit: int = 10) -> str:
    try:
        repo = get_repo()
        prs = list(repo.get_pulls(state="open"))[:limit]
        if not prs:
            return "No open pull requests."
        lines = []
        for pr in prs:
            author = pr.user.login
            draft = " [DRAFT]" if pr.draft else ""
            lines.append(f"#{pr.number} {pr.title}{draft} — {author} → {pr.base.ref}")
        return "\n".join(lines)
    except GithubException as e:
        return f"GitHub error: {e.data.get('message', str(e))}"
