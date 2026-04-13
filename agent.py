import os
import anthropic
from costs import record_anthropic_usage
from tools.github_tools import (
    list_repo_files,
    read_repo_file,
    get_github_issues,
    get_recent_commits,
    get_open_prs,
)
from tools.meta_tools import update_system_prompt, PROMPT_FILE

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

_PROMPT_PATH = os.path.join(os.path.dirname(__file__), PROMPT_FILE)


def _load_prompt() -> str:
    try:
        with open(_PROMPT_PATH) as f:
            return f.read().strip()
    except FileNotFoundError:
        return "You are a helpful project assistant."


# Mutable so the update_system_prompt tool can change it in-session
_system_prompt = _load_prompt()


def get_system_prompt() -> str:
    return _system_prompt + "\n\nRepo: " + os.getenv("GITHUB_REPO", "owner/repo")


TOOLS = [
    {
        "name": "list_repo_files",
        "description": "List files in a directory of the project repo. Use this to explore what docs/specs exist before reading them.",
        "input_schema": {
            "type": "object",
            "properties": {
                "directory": {
                    "type": "string",
                    "description": "Directory path to list, e.g. 'docs/' or '' for root.",
                }
            },
        },
    },
    {
        "name": "read_repo_file",
        "description": "Read the contents of a file from the project repo. Use for docs, READMEs, specs, architecture notes, etc.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "File path e.g. 'docs/architecture.md' or 'README.md'",
                }
            },
            "required": ["path"],
        },
    },
    {
        "name": "get_github_issues",
        "description": "Get issues from the GitHub repo. Useful for checking blockers, backlog, and what's been reported.",
        "input_schema": {
            "type": "object",
            "properties": {
                "state": {
                    "type": "string",
                    "enum": ["open", "closed", "all"],
                    "description": "Filter by issue state. Default: open",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max number of issues to return. Default: 10",
                },
                "label": {
                    "type": "string",
                    "description": "Filter by label e.g. 'bug', 'blocker', 'enhancement'",
                },
            },
        },
    },
    {
        "name": "get_recent_commits",
        "description": "Get recent commits to understand what has been built or changed lately.",
        "input_schema": {
            "type": "object",
            "properties": {
                "days": {
                    "type": "integer",
                    "description": "How many days back to look. Default: 7",
                },
                "branch": {
                    "type": "string",
                    "description": "Branch to check. Default: main",
                },
            },
        },
    },
    {
        "name": "get_open_prs",
        "description": "Get open pull requests — useful for seeing what's in progress or needs review.",
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Max number of PRs to return. Default: 10",
                }
            },
        },
    },
    {
        "name": "update_system_prompt",
        "description": (
            "Rewrite the bot's system prompt to persist a behavior change the user has requested. "
            "Pass the full updated prompt — not just the change. "
            "Use this when the user tells you to behave differently going forward."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "new_prompt": {
                    "type": "string",
                    "description": "The full new system prompt content.",
                }
            },
            "required": ["new_prompt"],
        },
    },
]


def execute_tool(name: str, inputs: dict) -> str:
    if name == "list_repo_files":
        return list_repo_files(inputs.get("directory", ""))
    elif name == "read_repo_file":
        return read_repo_file(inputs["path"])
    elif name == "get_github_issues":
        return get_github_issues(
            state=inputs.get("state", "open"),
            limit=inputs.get("limit", 10),
            label=inputs.get("label"),
        )
    elif name == "get_recent_commits":
        return get_recent_commits(
            days=inputs.get("days", 7),
            branch=inputs.get("branch", "main"),
        )
    elif name == "get_open_prs":
        return get_open_prs(limit=inputs.get("limit", 10))
    elif name == "update_system_prompt":
        global _system_prompt
        new_prompt = inputs["new_prompt"]
        result = update_system_prompt(new_prompt)
        # Apply immediately in-session too
        _system_prompt = new_prompt
        return result
    else:
        return f"Unknown tool: {name}"


def run_agent(user_message: str, sender: str, history: list = None) -> str:
    messages = list(history) if history else []
    messages.append({"role": "user", "content": f"[{sender}]: {user_message}"})

    for _ in range(10):  # max 10 tool calls per message
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=get_system_prompt(),
            tools=TOOLS,
            messages=messages,
        )

        record_anthropic_usage(response.usage.input_tokens, response.usage.output_tokens)

        if response.stop_reason == "end_turn":
            text_blocks = [b.text for b in response.content if hasattr(b, "text")]
            return "\n".join(text_blocks) or "Done."

        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})

            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = execute_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })

            messages.append({"role": "user", "content": tool_results})
        else:
            break

    return "I wasn't able to complete that — hit the tool call limit."
