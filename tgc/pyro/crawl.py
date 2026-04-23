import argparse
import asyncio
from pathlib import Path

from PIL import Image
from hypy_utils import printc, json_stringify, write
from hypy_utils.dict_utils import remove_keys
from telethon import TelegramClient, functions
from telethon.tl.custom.message import Message
from telethon.tl.types import PeerChannel, PeerUser, User

from .config import load_config, Config
from .consts import HTML
from .convert import convert_text, convert_media_dict
from .download_media import download_media, has_media, download_media_urlsafe, guess_ext
from .grouper import group_msgs
from ..convert_export import remove_nones
from ..convert_media_types import tgs_to_apng
from ..rss.posts_to_feed import posts_to_feed, FeedMeta


def effective_text(msg: Message) -> str | None:
    """
    Get effective text of a message in HTML
    """
    if msg.text:
        return convert_text(msg.text, msg.entities or [])
    if msg.message and msg.entities:
        return convert_text(msg.message, msg.entities)
    if msg.action:
        return str(msg.action).split(".")[-1].replace("_", " ").capitalize()
    return None


def get_user_name(user: User) -> str:
    name = user.first_name or ""
    if user.last_name:
        name += " " + user.last_name
    return name


async def get_forwarded_from(msg: Message) -> dict | None:
    fwd = msg.forward
    if not fwd:
        return None
    if getattr(fwd, "from_name", None):
        return {"name": fwd.from_name}

    from_id = getattr(fwd, "from_id", None)
    if isinstance(from_id, PeerUser):
        try:
            user = await app.get_entity(from_id.user_id)
            return {
                "name": get_user_name(user),
                "url": f"https://t.me/{user.username}" if user.username else None
            }
        except Exception:
            return None
    if isinstance(from_id, PeerChannel):
        try:
            chat = await app.get_entity(from_id.channel_id)
            return {"name": getattr(chat, "title", None)}
        except Exception:
            return None
    return None


async def process_message(msg: Message, path: Path, export: dict) -> dict:
    media_path = path / "media"

    m = {
        "id": msg.id,
        "date": msg.date,
        "type": 'service' if msg.action else None,
        "text": effective_text(msg),
        "author": msg.post_author,
        "views": msg.views,
        "forwards": msg.forwards,
        "forwarded_from": await get_forwarded_from(msg),
        "media_group_id": msg.grouped_id,
        "reply_id": msg.reply_to.reply_to_msg_id if msg.reply_to else None,
        "file": convert_media_dict(msg)
    }

    # Download file
    f = m.get('file')

    async def dl_media():
        fp, name = await download_media_urlsafe(
            app,
            msg,
            directory=media_path,
            max_file_size=int((export.get('size_limit_mb') or 0) * 1000_000),
        )
        if fp is None:
            return
        f['original_name'] = name

        # Convert tgs sticker
        if fp.suffix == '.tgs':
            fp = Path(tgs_to_apng(fp))

        f['url'] = str(fp.absolute().relative_to(path.absolute()))
        f['size'] = f.pop('file_size', None)

        # Download the largest thumbnail
        if f.get('thumbs'):
            ext = guess_ext(f.get("mime_type"), ".jpg")
            thumb_fp = await download_media(
                app,
                msg,
                directory=media_path,
                fname=fp.with_suffix(fp.suffix + f'_thumb{ext}').name,
                thumb=-1,
            )
            if thumb_fp:
                f['thumb'] = str(thumb_fp.absolute().relative_to(path.absolute()))
            del f['thumbs']

    if has_media(msg):
        await dl_media()

    # Move photo to its own key
    if f:
        mt = f.get('media_type')
        if mt == 'photo' or (not mt and (f.get('mime_type') or "").startswith("image")):
            img = m['image'] = m.pop('file')

            # Read image size
            img['width'], img['height'] = Image.open(path / img['url']).size

    return remove_keys(remove_nones(m), {'file_id', 'file_unique_id', 'file_reference', 'document', 'video_sizes'})


async def download_custom_emojis(msgs: list[Message], results: list[dict], path: Path):
    print("Downloading custom emojis...")
    # List custom emoji ids
    ids = {
        e.document_id
        for msg in msgs
        if msg.entities
        for e in msg.entities
        if getattr(e, "document_id", None)
    }
    ids = list(ids)

    if not ids:
        return

    docs = await app(functions.messages.GetCustomEmojiDocumentsRequest(document_id=ids))

    # Download stickers
    for document in docs:
        id = document.id
        ext = guess_ext(getattr(document, "mime_type", None), ".webp")
        op = await download_media(app, document, path / "emoji", f'{id}{ext}')
        if not op:
            continue
        op = op.absolute().relative_to(path.absolute())

        # Replace sticker paths
        for r in results:
            if "text" in r:
                r['text'] = r['text'].replace(
                    f'<i class="custom-emoji" emoji-src="emoji/{id}">',
                    f'<i class="custom-emoji" emoji-src="{op}">'
                )


async def process_chat(chat_id: int, path: Path, export: dict):
    chat = await app.get_entity(chat_id)
    printc(f"&aChat obtained. Chat name: {getattr(chat, 'title', 'Unknown')} | ID: {getattr(chat, 'id', chat_id)}")

    print("Crawling channel posts...")
    msgs = [m async for m in app.iter_messages(chat, reverse=True)]
    print(f"> {len(msgs)} total messages crawled.")

    results = [await process_message(m, path, export) for m in msgs]
    await download_custom_emojis(msgs, results, path)

    # Group messages
    results = group_msgs(results)

    write(path / "posts.json", json_stringify(results, indent=2))
    write(path / "index.html", HTML.replace("$$POSTS_DATA$$", json_stringify(results)))

    if 'rss' in export:
        print("Exporting RSS feed...")
        posts_to_feed(path, FeedMeta(**export['rss']))

    printc(f"&aDone! Saved to {path / 'posts.json'}")


async def run_app():
    me = await app.get_me()
    printc(f"&aLogin success! ID: {me.id} | is_bot: {me.bot}")
    for export in cfg.exports:
        await process_chat(int(export["chat_id"]), Path(export["path"]), export)


cfg: Config
app: TelegramClient


def run():
    global app, cfg
    parser = argparse.ArgumentParser("Telegram Channel Message to Public API Crawler")
    parser.add_argument("config", help="Config path", nargs="?", default="config.toml")
    args = parser.parse_args()
    cfg = load_config(args.config)

    app = TelegramClient(
        "Bot",
        cfg.api_id or 2048,
        cfg.api_hash or "b18441a1ff607e10a989891a5462e627",
    )

    with app:
        if cfg.bot_token:
            app.loop.run_until_complete(app.start(bot_token=cfg.bot_token))
        else:
            app.loop.run_until_complete(app.start())
        app.loop.run_until_complete(run_app())
