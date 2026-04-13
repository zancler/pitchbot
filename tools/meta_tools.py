import os
from github import Github, GithubException

PROMPT_FILE = "system_prompt.txt"


def update_system_prompt(new_prompt: str) -> str:
    """Rewrite system_prompt.txt in the repo via GitHub API and commit it."""
    try:
        # Use a separate token for writing to the bot's own repo
        token = os.environ.get("PITCHBOT_GITHUB_TOKEN", os.environ["GITHUB_TOKEN"])
        g = Github(token)
        # Always commit back to the bot's own repo, not the project repo
        repo = g.get_repo(os.environ.get("PITCHBOT_REPO", "zancler/pitchbot"))

        try:
            existing = repo.get_contents(PROMPT_FILE)
            repo.update_file(
                PROMPT_FILE,
                "Update system prompt via bot instruction",
                new_prompt,
                existing.sha,
            )
        except GithubException:
            repo.create_file(
                PROMPT_FILE,
                "Create system prompt file",
                new_prompt,
            )

        return (
            "Done — behavior saved to the repo. "
            "A redeploy will kick off automatically (takes ~2 min). "
            "I've already applied the change in this session."
        )
    except Exception as e:
        return f"Error saving behavior change: {e}"
