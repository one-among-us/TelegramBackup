import argparse
import asyncio
from pathlib import Path

import uvloop
from hypy_utils import printc, json_stringify, write
from hypy_utils.dict_utils import remove_keys
from pyrogram import Client
from pyrogram.file_id import FileId
from pyrogram.types import User, Chat, Message

from .config import load_config, Config
from .convert import convert_text, convert_media_dict
from .download_media import download_media, has_media, guess_ext
from .grouper import group_msgs
from ..convert_export import remove_nones

MEDIA_PATH = Path("media")
uvloop.install()


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


def _download_media_helper(args: list) -> Path:
    return asyncio.run(download_media(app, *args))


async def process_message(msg: Message, path: Path) -> dict:
    m = {
        "id": msg.id,
        "date": msg.date,
        "text": effective_text(msg),
        "author": msg.author_signature,
        "views": msg.views,
        "forwards": msg.forwards,
        "reply_id": msg.reply_to_message_id,
        "file": convert_media_dict(msg)
    }

    # Download file
    if has_media(msg):
        fp = await download_media(app, msg, directory=path / "media")
        f = m['file']
        f['url'] = str(fp.absolute().relative_to(path.absolute()))

        # Download the largest thumbnail
        if f.get('thumbs'):
            thumb: dict = max(f['thumbs'], key=lambda x: x['file_size'])
            ext = guess_ext(app, FileId.decode(thumb['file_id']).file_type, None)
            fp = await download_media(app, thumb['file_id'], directory=path / "media",
                                      fname=fp.with_suffix(fp.suffix + f'_thumb{ext}').name)
            f['thumb'] = str(fp.absolute().relative_to(path.absolute()))
            del f['thumbs']

    return remove_keys(remove_nones(m), {'file_id', 'file_unique_id'})


async def process_chat(chat_id: int, path: Path):
    chat: Chat = await app.get_chat(chat_id)
    printc(f"&aChat obtained. Chat name: {chat.title} | Type: {chat.type} | ID: {chat.id}")

    # Crawl messages
    msgs = await app.get_messages(chat.id, range(1, 40))

    # print(msgs)
    results = [await process_message(m, path) for m in msgs if not m.empty]

    # Group messages
    results = group_msgs(results)

    write(path / "posts.json", json_stringify(results, indent=2))


async def run_app():
    me: User = await app.get_me()
    printc(f"&aLogin success! ID: {me.id} | is_bot: {me.is_bot}")
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
