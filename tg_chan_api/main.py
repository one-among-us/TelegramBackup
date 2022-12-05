import argparse
import asyncio
from pathlib import Path
from typing import BinaryIO

import uvloop
from hypy_utils.tqdm_utils import tmap
from pyrogram import Client
from pyrogram.types import User, Chat, Message, Photo
from ruamel import yaml

from tg_chan_api.download_media import download_media

MEDIA_PATH = Path("media")
uvloop.install()


def load_config(path: str) -> dict[str, str]:
    with open(path, "r") as f:
        return yaml.safe_load(f)


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
    if msg.text:
        return msg.text.markdown
    if msg.caption:
        return msg.caption.markdown
    if msg.service:
        return str(msg.service)


def _download_media_helper(args: list) -> Path:
    return asyncio.run(download_media(app, *args))


async def process_messages(msgs: list[Message]):
    # 1. Download media
    # media_msgs = [[m] for m in msgs if m.media]
    # fps: list[Path] = smap(_download_media_helper, media_msgs)
    # print([fp.relative_to(Path().absolute()) for fp in fps])
    for m in msgs:
        if m.media:
            fp = await download_media(app, m)
            fp = fp.absolute().relative_to(Path().absolute())


async def run(app: Client):
    me: User = await app.get_me()
    print(f"Login success! ID: {me.id} | is_bot: {me.is_bot}")
    chat: Chat = await app.get_chat(cfg['chat_id'])
    print(f"Chat obtained. Chat name: {chat.title} | Type: {chat.type} | ID: {chat.id}")
    # Bot
    msgs = await app.get_messages(chat.id, range(1, 30))
    # print('\n'.join([f'{m.id}: {effective_text(m)}' for m in msgs if not m.empty]))
    print(msgs)
    await process_messages(msgs)


if __name__ == '__main__':
    parser = argparse.ArgumentParser("Telegram Channel Message to Public API Crawler")
    parser.add_argument("config", help="Config path", nargs="?", default="config.yml")
    args = parser.parse_args()
    cfg = load_config(args.config)

    app = Client("Bot", cfg["api_id"], cfg["api_hash"], bot_token=cfg["bot_token"])

    with app:
        asyncio.get_event_loop().run_until_complete(run(app))
