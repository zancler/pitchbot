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

_bot_user_id: str = None


def get_bot_user_id() -> str:
    global _bot_user_id
    if _bot_user_id is None:
        try:
            _bot_user_id = app.client.auth_test()["user_id"]
            logger.info(f"Bot user ID: {_bot_user_id}")
        except Exception as e:
            logger.error(f"Failed to get bot user ID: {e}")
    return _bot_user_id


def post(channel: str, text: str, thread_ts: str = None):
    """Post a message, always in a thread if thread_ts is given."""
    kwargs = {"channel": channel, "text": text}
    if thread_ts:
        kwargs["thread_ts"] = thread_ts
    logger.info(f"Posting to {channel} thread_ts={thread_ts}")
    app.client.chat_postMessage(**kwargs)


def get_thread_history(channel: str, thread_ts: str) -> list:
    """Fetch previous messages in a thread and format as Claude conversation history."""
    try:
        result = app.client.conversations_replies(channel=channel, ts=thread_ts)
        messages = result.get("messages", [])[:-1]  # exclude current message
        history = []
        bot_id = get_bot_user_id()
        for msg in messages:
            text = msg.get("text", "").strip()
            if not text:
                continue
            if msg.get("user") == bot_id or msg.get("bot_id"):
                history.append({"role": "assistant", "content": text})
            else:
                sender = get_user_name(msg.get("user", "unknown"))
                history.append({"role": "user", "content": f"[{sender}]: {text}"})
        return history
    except Exception as e:
        logger.error(f"Failed to fetch thread history: {e}")
        return []


def bot_is_in_thread(channel: str, thread_ts: str) -> bool:
    """Check Slack thread history to see if the bot has already replied."""
    try:
        bot_id = get_bot_user_id()
        if not bot_id:
            logger.warning("No bot user ID, skipping thread check")
            return False
        result = app.client.conversations_replies(channel=channel, ts=thread_ts)
        messages = result.get("messages", [])
        in_thread = any(msg.get("user") == bot_id for msg in messages)
        logger.info(f"Thread check {thread_ts}: {len(messages)} messages, bot_in_thread={in_thread}")
        return in_thread
    except Exception as e:
        logger.error(f"Thread check failed: {e}")
        return False


@app.event("app_mention")
def handle_mention(event, say):
    """Respond when the bot is @mentioned in a channel."""
    user_id = event["user"]
    sender = get_user_name(user_id)
    channel = event["channel"]
    thread_ts = event.get("thread_ts", event["ts"])

    user_message = " ".join(
        word for word in event["text"].split()
        if not word.startswith("<@")
    ).strip()

    logger.info(f"Mention: channel={channel}, thread_ts={thread_ts}, msg={user_message[:50]}")

    if not user_message:
        post(channel, "Hey! Ask me anything about the project.", thread_ts)
        return

    try:
        history = get_thread_history(channel, thread_ts) if thread_ts else []
        reply = run_agent(user_message, sender, history)
        post(channel, reply, thread_ts)
        _maybe_warn_cost(channel, thread_ts)
    except Exception as e:
        logger.error(f"Error: {e}")
        post(channel, "Something went wrong — check the logs.", thread_ts)


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

    # DMs — always respond
    if channel_type == "im":
        try:
            reply = run_agent(user_message, sender)
            post(channel, reply)
            _maybe_warn_cost(channel, None)
        except Exception as e:
            logger.error(f"Error: {e}")
            post(channel, "Something went wrong — check the logs.")

    # Channel thread messages — only if bot is already in the thread
    elif thread_ts and bot_is_in_thread(channel, thread_ts):
        try:
            history = get_thread_history(channel, thread_ts)
            reply = run_agent(user_message, sender, history)
            post(channel, reply, thread_ts)
            _maybe_warn_cost(channel, thread_ts)
        except Exception as e:
            logger.error(f"Error: {e}")
            post(channel, "Something went wrong — check the logs.", thread_ts)


def _maybe_warn_cost(channel: str, thread_ts: str = None):
    threshold = check_thresholds()
    if threshold is not None:
        post(channel, f":warning: Cost alert: total usage has crossed ${threshold:.0f}. {cost_summary()}", thread_ts)


def get_user_name(user_id: str) -> str:
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
