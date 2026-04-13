# PM Agent 🤖

A Claude-powered Slack bot that acts as your project's product manager. It has full context about what you're building — it can read your GitHub docs, check issues and PRs, and see recent commits. Talk to it by @mentioning it in a channel, or DM it directly.

## What it can do

- Read any file in your repo (docs, specs, READMEs, architecture notes)
- Browse your docs directory to find relevant files
- Check open/closed GitHub issues (supports label filtering e.g. "blocker")
- See recent commits on any branch
- View open pull requests and their status

## Project structure

```
pm-agent/
├── bot.py              # Slack event handlers (@mention and DMs)
├── agent.py            # Claude tool loop — the core brain
├── tools/
│   └── github_tools.py # All GitHub API calls
├── requirements.txt
├── Dockerfile
├── fly.toml            # Fly.io deployment config
└── .env.example        # Environment variable reference
```

## Setup

### 1. Create a Slack app

1. Go to [api.slack.com/apps](https://api.slack.com/apps) and click **Create New App > From scratch**
2. Give it a name (e.g. "PM Agent") and pick your workspace

**Enable Socket Mode** (so it doesn't need a public URL):
- Go to **Socket Mode** in the left sidebar → toggle it on
- Create an App-Level Token with the `connections:write` scope
- Copy the token — this is your `SLACK_APP_TOKEN` (starts with `xapp-`)

**Add Bot Permissions:**
- Go to **OAuth & Permissions > Bot Token Scopes** and add:
  - `app_mentions:read` — to hear @mentions
  - `chat:write` — to send messages
  - `im:history` — to receive DMs
  - `im:write` — to send DMs
  - `users:read` — to look up user display names

**Subscribe to Events:**
- Go to **Event Subscriptions** → toggle on
- Under **Subscribe to bot events**, add:
  - `app_mention`
  - `message.im`

**Install the app:**
- Go to **OAuth & Permissions** → click **Install to Workspace**
- Copy the **Bot User OAuth Token** — this is your `SLACK_BOT_TOKEN` (starts with `xoxb-`)

**Invite the bot to a channel:**
- In Slack, go to the channel you want to use and type `/invite @PM Agent`

### 2. Get your other API keys

- **Anthropic API key**: [console.anthropic.com](https://console.anthropic.com)
- **GitHub token**: [github.com/settings/tokens](https://github.com/settings/tokens) — needs `repo` scope for private repos

### 3. Configure environment variables

```bash
cp .env.example .env
# Fill in your values
```

### 4. Run locally (to test before deploying)

```bash
pip install -r requirements.txt
python bot.py
```

Then @mention the bot in Slack or send it a DM. If it responds, you're good to deploy.

### 5. Deploy to Fly.io

```bash
# Install the Fly CLI
brew install flyctl        # macOS
# or: curl -L https://fly.io/install.sh | sh

# Login / sign up
fly auth signup            # or: fly auth login

# From inside this project folder:
fly launch --no-deploy     # sets up the app — say yes to using existing fly.toml

# Set your environment variables
fly secrets set SLACK_BOT_TOKEN=xoxb-xxx
fly secrets set SLACK_APP_TOKEN=xapp-xxx
fly secrets set ANTHROPIC_API_KEY=xxx
fly secrets set GITHUB_TOKEN=xxx
fly secrets set GITHUB_REPO=yourname/your-repo

# Deploy!
fly deploy
```

After that it runs 24/7 on Fly's free tier. To redeploy after code changes, just run `fly deploy` again.

**Note:** In `fly.toml`, change `your-pm-agent` to a unique app name (it's a global namespace), and update `primary_region` to your nearest location (`lhr` = London, `iad` = US East, `sea` = US West). Full region list: [fly.io/docs/reference/regions](https://fly.io/docs/reference/regions/)

## Environment variables

| Variable | Description |
|----------|-------------|
| `SLACK_BOT_TOKEN` | Bot User OAuth Token from api.slack.com/apps (starts with `xoxb-`) |
| `SLACK_APP_TOKEN` | App-Level Token for Socket Mode (starts with `xapp-`) |
| `ANTHROPIC_API_KEY` | From console.anthropic.com |
| `GITHUB_TOKEN` | Personal access token with `repo` scope |
| `GITHUB_REPO` | Your repo in `owner/repo` format |

## Customising the system prompt

Edit `SYSTEM_PROMPT` in `agent.py` to tell the bot more about your project — what you're building, your tech stack, your current priorities. The more context you give it here, the better its answers will be.

Example additions:
```
We are building a B2B SaaS tool for logistics companies. Our stack is Next.js, 
FastAPI, and Postgres. We are pre-launch, currently focused on our first 3 pilot customers.
Our docs are in the /docs folder, organised by feature area.
```

## Adding more tools

1. Add a new function to `tools/github_tools.py` (or create a new file e.g. `tools/notion_tools.py`)
2. Add a tool definition to the `TOOLS` list in `agent.py`
3. Add the case to `execute_tool()` in `agent.py`

## Usage

- **In a channel**: `@PM Agent what are our open blockers?`
- **DM**: Just message it directly, no need to @mention
- **Examples**:
  - "What did we build this week?"
  - "What's blocking us right now?"
  - "Summarise the auth docs"
  - "Any PRs waiting for review?"
  - "What does our onboarding flow look like?"
