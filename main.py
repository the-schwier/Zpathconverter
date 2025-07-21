import logging
import os
import re
import threading
import time

from flask import Flask
from slack_sdk import WebClient
from slack_sdk.socket_mode import SocketModeClient
from slack_sdk.socket_mode.request import SocketModeRequest
from slack_sdk.socket_mode.response import SocketModeResponse

# Environment variables
SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
SLACK_APP_TOKEN = os.environ["SLACK_APP_TOKEN"]

# Slack clients
web_client = WebClient(token=SLACK_BOT_TOKEN)
socket_client = SocketModeClient(app_token=SLACK_APP_TOKEN, web_client=web_client)

# Logging
logging.basicConfig(level=logging.INFO)

# Flask keep-alive server
app = Flask(__name__)


@app.route("/")
def index():
    return "Zpathconverter is alive!"


def start_flask():
    app.run(host="0.0.0.0", port=8080)


# Path conversion


def convert_path(text):
    original_text = text

    # Convert Mac → Windows
    if "/Volumes/Projects" in text:
        text = re.sub(
            r"/Volumes/Projects([^\s]+)",
            lambda m: r"Z:" + m.group(1).replace("/", "\\"),
            text,
        )
    # Convert Windows → Mac
    elif re.search(r"Z:[\\/]+[^\s]+", text):
        text = re.sub(
            r"Z:[\\/]+([^\s]+)",
            lambda m: "/Volumes/Projects/" + m.group(1).replace("\\", "/"),
            text,
        )

    if "123456" in text:
        text = "hello sir"
    return text if text != original_text else None


# Handle incoming Slack messages
def handle_message(payload):
    event = payload.get("event", {})
    text = event.get("text", "")
    user = event.get("user")
    channel = event.get("channel")

    if event.get("bot_id") is not None:
        return

    if not user or not text:
        return

    converted = convert_path(text.strip())
    if converted:
        web_client.chat_postMessage(channel=channel, text=converted)


def process_socket_mode_request(client: SocketModeClient, req: SocketModeRequest):
    logging.info(f"📥 Request type: {req.type}")
    try:
        client.send_socket_mode_response(
            SocketModeResponse(envelope_id=req.envelope_id)
        )
        if req.type == "events_api":
            handle_message(req.payload)
    except Exception as e:
        logging.error(f"⚠️ Error processing request: {e}")


# Start Slack bot
def start_slack_bot():
    socket_client.socket_mode_request_listeners.append(process_socket_mode_request)
    socket_client.connect()


if __name__ == "__main__":
    logging.info("🚀 Keep-alive server started.")

    # Start Flask in background thread
    threading.Thread(target=start_flask, daemon=True).start()

    # Start Slack bot in foreground
    logging.info("🤖 Bot connecting to Slack...")
    start_slack_bot()

    # Prevent main thread from exiting
    while True:
        time.sleep(10)
