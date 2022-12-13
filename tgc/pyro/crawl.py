import argparse
import asyncio
from pathlib import Path

import uvloop
from pyrogram import Client
from pyrogram.enums import MessageMediaType
from pyrogram.types import User, Chat, Message

from .config import load_config, Config
from .convert import convert_text
from .download_media import download_media
from ..convert_export import remove_nones

MEDIA_PATH = Path("media")
uvloop.install()


def parse_msg(msg: Message) -> dict | None:
    if msg.empty:
        return None

    ty = None
    text = msg.text.markdown
    if msg.service:
        ty = "service"
        text = msg.service.value + msg.text

    return {k: v for k, v in {
        'id': msg.id,
        'date': msg.date,
        'type': ty,
        'text': text,
        'views': msg.views
    }.items() if v is not None}


def effective_text(msg: Message) -> str:
    """
    Get effective text of a message in HTML
    """
    if msg.text:
        return convert_text(msg.text, msg.text.entities)
    if msg.caption:
        return convert_text(msg.caption, msg.caption.entities)
    if msg.service:
        return str(msg.service)


MEDIA_TYPE_MAP: dict[MessageMediaType, str] = {
    MessageMediaType.STICKER: "sticker",
    MessageMediaType.VOICE: "voice_message",
    MessageMediaType.AUDIO: "audio_file",
    MessageMediaType.ANIMATION: "animation",
    MessageMediaType.VIDEO: "video_file",
    MessageMediaType.VIDEO_NOTE: "video_file",

    # TODO: Support these in web ui
    MessageMediaType.CONTACT: "contact",
    MessageMediaType.POLL: "poll",
    MessageMediaType.WEB_PAGE: "web_page",
    MessageMediaType.LOCATION: "location",
    MessageMediaType.VENUE: "location"
}


def _download_media_helper(args: list) -> Path:
    return asyncio.run(download_media(app, *args))


def process_message(msg: Message) -> dict:
    m = {
        "id": msg.id,
        "date": msg.date,
        "text": effective_text(msg),
        "author": msg.author_signature,
        "views": msg.views,
        "forwards": msg.forwards
    }

    return remove_nones(m)


async def process_messages(msgs: list[Message], path: Path):
    # 1. Download media
    # media_msgs = [[m] for m in msgs if m.media]
    # fps: list[Path] = smap(_download_media_helper, media_msgs)
    # print([fp.relative_to(Path().absolute()) for fp in fps])
    for m in msgs:
        if m.media:
            fp = await download_media(app, m)
            fp = fp.absolute().relative_to(Path().absolute())


async def process_chat(chat_id: int, path: Path):
    chat: Chat = await app.get_chat(chat_id)
    print(f"Chat obtained. Chat name: {chat.title} | Type: {chat.type} | ID: {chat.id}")

    # Crawl messages
    msgs = await app.get_messages(chat.id, range(1, 40))

    # for m in msgs:
    #     print(type(m.media))

    # print('\n'.join([f'{m.id}: {effective_text(m)}' for m in msgs if not m.empty]))
    print(msgs)
    # await process_messages(msgs, path)


async def run_app():
    me: User = await app.get_me()
    print(f"Login success! ID: {me.id} | is_bot: {me.is_bot}")
    for export in cfg.exports:
        await process_chat(int(export["chat_id"]), Path(export["path"]))


cfg: Config
app: Client


def run():
    global app, cfg
    parser = argparse.ArgumentParser("Telegram Channel Message to Public API Crawler")
    parser.add_argument("config", help="Config path", nargs="?", default="config.toml")
    args = parser.parse_args()
    cfg = load_config(args.config)

    app = Client("Bot", cfg.api_id, cfg.api_hash, bot_token=cfg.bot_token)

    with app:
        asyncio.get_event_loop().run_until_complete(run_app())
