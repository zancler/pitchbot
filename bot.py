import os
import logging
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from agent import run_agent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = App(token=os.environ["SLACK_BOT_TOKEN"])


@app.event("app_mention")
def handle_mention(event, say):
    """Respond when the bot is @mentioned in a channel."""
    user_message = event["text"]
    user_id = event["user"]
    sender = get_user_name(user_id)

    # Strip the bot mention from the message
    user_message = " ".join(
        word for word in user_message.split()
        if not word.startswith("<@")
    ).strip()

    if not user_message:
        say("Hey! Ask me anything about the project.")
        return

    try:
        reply = run_agent(user_message, sender)
        say(reply)
    except Exception as e:
        logger.error(f"Error: {e}")
        say("Something went wrong — check the logs.")


@app.event("message")
def handle_dm(event, say):
    """Respond to direct messages."""
    # Ignore messages from bots and message subtypes (edits, deletions etc)
    if event.get("bot_id") or event.get("subtype"):
        return
    # Only handle DMs (channel_type = "im")
    if event.get("channel_type") != "im":
        return

    user_message = event.get("text", "").strip()
    if not user_message:
        return

    user_id = event["user"]
    sender = get_user_name(user_id)

    try:
        reply = run_agent(user_message, sender)
        say(reply)
    except Exception as e:
        logger.error(f"Error: {e}")
        say("Something went wrong — check the logs.")


def get_user_name(user_id: str) -> str:
    """Resolve a Slack user ID to a display name."""
    try:
        result = app.client.users_info(user=user_id)
        return result["user"]["real_name"] or result["user"]["name"]
    except Exception:
        return user_id


def main():
    handler = SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    logger.info("PM Agent is running on Slack...")
    handler.start()


if __name__ == "__main__":
    main()
