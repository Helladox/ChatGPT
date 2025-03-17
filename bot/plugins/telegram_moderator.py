import os
from dotenv import load_dotenv
from typing import Dict, List
from .plugin import Plugin

from telegram import Bot, Update
from telegram.error import TelegramError

# Load environment variables from .env file.
load_dotenv()

# Configuration values from environment variables.
BOT_TOKEN_MODERATOR = os.getenv("BOT_TOKEN_MODERATOR", "")
CHANNEL_ID = os.getenv("CHANNEL_ID", "")
GROUP_ID = os.getenv("GROUP_ID", "")

class TelegramModerator(Plugin):
    """
    A Telegram plugin that handles messages by either forwarding them or sending new messages
    to a specific channel based on keywords.
    """

    def get_source_name(self) -> str:
        return "TelegramModerator"

    def get_spec(self) -> List[Dict]:
        # Return the JSON schema for the handle_message function.
        return [{
            "name": "telegram_moderator",
            "description": (
                "Handles a Telegram message. If the message starts with 'forward it :', the message is "
                "forwarded to a designated channel. If it starts with 'send it :', the text is sent as a "
                "new message to the channel. If it starts with 'get recent', the bot retrieves recent messages."
                "If it starts with 'close_topic', the bot closes a forum topic. If it starts with 'open_topic', "
                "the bot opens a forum topic."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["send_to_channel", "send_to_topic", "get_recent_chats", "close_topic", "re-open_topic", "forward_to_channel"],
                        "description": "The action to perform:"
                        "## for channel:" 
                        "'send_to_channel' sends a new message to the channel. Distinct between this and 'send_to_topic'"
                        "'forward_to_channel' forwards a message to the channel."
                        " "
                        "## for group and its topic"
                        "'send_to_topic' sends a new message to the topic. **Use with caution!**"
                        "'get_recent_chats' retrieves recent chats. " 
                        "'close_topic' closes a forum topic and 'open_topic' opens a forum topic. **Use with caution!**"
                        "'re-open_topic' re-opens a previously closed topic."
                    },
                    "message_text": {
                        "type": "string",
                        "description": "The full text of the Telegram message."
                    },
                    "group_id": {
                        "type": "integer",
                        "description": "The group_id. Must be provided for actions related to topics."
                    },
                    "message_thread_id": {
                        "type": "integer",
                        "description": "The message_thread_id of the topic to manage. Must be provided for actions related to topics."
                    },
                    "message_id": {
                        "type": "integer",
                        "description": "The ID of the message to forward. Required for 'forward_to_channel' action."
                    }
                },
                "required": ["action","message_text","group_id","message_thread_id","message_id"]
            }
        }]

    async def execute(self, function_name: str, helper, **kwargs) -> Dict:
        # Basic configuration checks.
        if not BOT_TOKEN_MODERATOR:
            return {"error": "BOT_TOKEN is missing from environment variables."}

        if not CHANNEL_ID:
            return {"error": "CHANNEL_ID is missing from environment variables."}

        if not GROUP_ID:
            return {"error": "GROUP_ID is missing from environment variables."}

        # Unpack required parameters.
        action = kwargs.get("action")
        group_id = kwargs.get("group_id")
        message_text = kwargs.get("message_text")
        message_thread_id = kwargs.get("message_thread_id")
        message_id = kwargs.get("message_id")

        # Initialize the Telegram Bot.
        bot = Bot(token=BOT_TOKEN_MODERATOR)

        try:
            if action == "send_to_channel":
                # Send a new message to the channel.
                await bot.send_message(chat_id=CHANNEL_ID, text=message_text)
                return {"status": "success", "action": "send", "details": message_text}

            elif action == "forward_to_channel":
                if not message_id:
                    return {"error": "message_id is required to forward a message."}
                await bot.forward_message(chat_id=CHANNEL_ID, from_chat_id=group_id, message_id=message_id)
                return {"status": "success", "action": "forward", "details": f"Message {message_id} forwarded to channel {CHANNEL_ID}"}

            elif action == "get_recent_chats":
                # Retrieve pending updates from the bot.
                updates = await bot.get_updates(offset=0, timeout=10)
                messages = []
                for idx, update in enumerate(updates, start=1):
                    if update.effective_message :
                        text = update.effective_message.text or "No text"
                        thread_id = getattr(update.message, "message_thread_id", None)
                        chat_id = update.message.chat.id
                        messages.append(f"Text: {text}, Thread ID: {thread_id}, Chat ID: {chat_id}")
                # Return the details of the last 10 messages.
                result = "\n".join(messages[-10:])
                return {"status": "success", "action": "get_recent", "details": result}

            elif action == "send_to_topic":
                # Send a new message to the topic.
                await bot.send_message(chat_id=group_id, message_thread_id=message_thread_id, text=message_text)
                return {"status": "success", "action": "send", "details": f"sent the message:`{message_text}` successfully"}

            elif action == "close_topic":
                if not message_thread_id:
                    return {"error": "message_thread_id is required to close a topic."}
                await bot.close_forum_topic(chat_id=group_id, message_thread_id=message_thread_id)
                await bot.send_message(chat_id=group_id, message_thread_id=message_thread_id, text=f"{message_text}\n 🤖by Moderator bot✍🏻")
                return {"status": "success", "action": "close_topic", "details": f"Topic {message_thread_id} closed in group {group_id}"}

            elif action == "re-open_topic":
                if not message_thread_id:
                    return {"error": "message_thread_id is required to open a topic."}
                await bot.open_forum_topic(chat_id=group_id, message_thread_id=message_thread_id)
                await bot.send_message(chat_id=group_id, message_thread_id=message_thread_id, text=f"{message_text} \n 🤖by Moderator bot✍🏻")
                return {"status": "success", "action": "open_topic", "details": f"Topic {message_thread_id} opened in group {group_id}"}



            else:
                return {"status": "success", "action": "process", "details": "Invalid action provided"}

        except TelegramError as e:
            return {"error": f"Telegram error: {e}"}
        except Exception as ex:
            return {"error": f"Unexpected error: {ex}"}
