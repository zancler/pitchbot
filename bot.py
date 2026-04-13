import os
import logging
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from dotenv import load_dotenv
from agent import run_agent
from costs import check_thresholds, cost_summary

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = App(token=os.environ["SLACK_BOT_TOKEN"])

# Cache the bot's own user ID so we can check thread history
_bot_user_id: str = None


def get_bot_user_id() -> str:
    global _bot_user_id
    if _bot_user_id is None:
        _bot_user_id = app.client.auth_test()["user_id"]
    return _bot_user_id


def bot_is_in_thread(channel: str, thread_ts: str) -> bool:
    """Check Slack thread history to see if the bot has already replied."""
    try:
        result = app.client.conversations_replies(channel=channel, ts=thread_ts)
        bot_id = get_bot_user_id()
        return any(
            msg.get("user") == bot_id
            for msg in result.get("messages", [])
        )
    except Exception:
        return False


@app.event("app_mention")
def handle_mention(event, say):
    """Respond when the bot is @mentioned in a channel."""
    user_message = event["text"]
    user_id = event["user"]
    sender = get_user_name(user_id)
    channel = event["channel"]
    thread_ts = event.get("thread_ts", event["ts"])

    # Strip the bot mention from the message
    user_message = " ".join(
        word for word in user_message.split()
        if not word.startswith("<@")
    ).strip()

    if not user_message:
        say("Hey! Ask me anything about the project.", thread_ts=thread_ts)
        return

    try:
        reply = run_agent(user_message, sender)
        say(reply, thread_ts=thread_ts)
        _maybe_warn_cost(say, thread_ts)
    except Exception as e:
        logger.error(f"Error: {e}")
        say("Something went wrong — check the logs.", thread_ts=thread_ts)


@app.event("message")
def handle_message(event, say):
    """Respond to DMs and thread messages where the bot is already active."""
    if event.get("bot_id") or event.get("subtype"):
        return

    channel_type = event.get("channel_type")
    channel = event["channel"]
    thread_ts = event.get("thread_ts")
    user_message = event.get("text", "").strip()
    user_id = event.get("user")

    if not user_message or not user_id:
        return

    sender = get_user_name(user_id)

    # DMs — always respond (no threading in DMs)
    if channel_type == "im":
        try:
            reply = run_agent(user_message, sender)
            say(reply)
            _maybe_warn_cost(say, None)
        except Exception as e:
            logger.error(f"Error: {e}")
            say("Something went wrong — check the logs.")

    # Channel messages — only respond if bot is already in the thread
    elif thread_ts and bot_is_in_thread(channel, thread_ts):
        try:
            reply = run_agent(user_message, sender)
            say(reply, thread_ts=thread_ts)
            _maybe_warn_cost(say, thread_ts)
        except Exception as e:
            logger.error(f"Error: {e}")
            say("Something went wrong — check the logs.", thread_ts=thread_ts)


def _maybe_warn_cost(say, thread_ts=None):
    threshold = check_thresholds()
    if threshold is not None:
        kwargs = {"thread_ts": thread_ts} if thread_ts else {}
        say(f":warning: Cost alert: total usage has crossed ${threshold:.0f}. {cost_summary()}", **kwargs)


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
