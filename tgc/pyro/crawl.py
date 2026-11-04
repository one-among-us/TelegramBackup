import argparse
import asyncio
import json
from pathlib import Path

from PIL import Image
from hypy_utils import printc, json_stringify, write
from hypy_utils.dict_utils import remove_keys
from pyrogram import Client
from pyrogram.file_id import FileId
from pyrogram.types import User, Chat, Message, Sticker

from .config import load_config, Config
from .consts import HTML
from .convert import convert_text, convert_media_dict
from .download_media import download_media, has_media, guess_ext, download_media_urlsafe
from .grouper import group_msgs
from ..convert_export import remove_nones
from ..convert_media_types import tgs_to_apng
from ..rss.posts_to_feed import posts_to_feed, FeedMeta


def effective_text(msg: Message) -> str:
    """
    Get effective text of a message in HTML
    """
    if msg.text:
        return convert_text(msg.text, msg.text.entities)
    if msg.caption:
        return convert_text(msg.caption, msg.caption.entities)
    if msg.service:
        return str(msg.service).split(".")[-1].replace("_", " ").capitalize()


def _download_media_helper(args: list) -> Path:
    return asyncio.run(download_media(app, *args))


def get_user_name(user: User) -> str:
    name = user.first_name or ""
    if user.last_name:
        name += " " + user.last_name
    return name


def get_forward_info(msg: Message) -> dict | None:
    origin = getattr(msg, "forward_origin", None)
    if origin is not None:
        sender_user = getattr(origin, "sender_user", None)
        if sender_user:
            return {
                "name": get_user_name(sender_user),
                "url": f'https://t.me/{sender_user.username}' if sender_user.username else None,
            }
        chat = getattr(origin, "chat", getattr(origin, "sender_chat", None))
        if chat:
            return {"name": chat.title}
        sender_name = getattr(origin, "sender_user_name", None)
        if sender_name:
            return {"name": sender_name}
        return None

    if getattr(msg, "forward_from", None):
        return {
            "name": get_user_name(msg.forward_from),
            "url": f'https://t.me/{msg.forward_from.username}' if msg.forward_from.username else None,
        }
    if getattr(msg, "forward_from_chat", None):
        return {"name": msg.forward_from_chat.title}
    if getattr(msg, "forward_sender_name", None):
        return {"name": msg.forward_sender_name}
    return None


async def process_message(msg: Message, path: Path, export: dict) -> dict:
    media_path = path / "media"

    m = {
        "id": msg.id,
        "date": msg.date,
        "type": 'service' if msg.service else None,
        "text": effective_text(msg),
        "author": msg.author_signature,
        "views": msg.views,
        "forwards": msg.forwards,
        "forwarded_from": get_forward_info(msg),
        "media_group_id": msg.media_group_id,
        "reply_id": msg.reply_to_message_id,
        "file": convert_media_dict(msg)
    }

    # Download file
    f = m.get('file')

    async def dl_media():
        fp, name = await download_media_urlsafe(app, msg, directory=media_path,
                                                max_file_size=int((export.get('size_limit_mb') or 0) * 1000_000))
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
            thumb: dict = max(f['thumbs'], key=lambda x: x['file_size'])
            ext = guess_ext(app, FileId.decode(thumb['file_id']).file_type, None)
            fp = await download_media(app, thumb['file_id'], directory=media_path,
                                      fname=fp.with_suffix(fp.suffix + f'_thumb{ext}').name)
            f['thumb'] = str(fp.absolute().relative_to(path.absolute()))
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

    return remove_keys(remove_nones(m), {'file_id', 'file_unique_id'})


async def download_custom_emojis(msgs: list[Message], results: list[dict], path: Path):
    print("Downloading custom emojis...")
    # List custom emoji ids
    ids = {e.custom_emoji_id for msg in msgs if msg.text and msg.text.entities for e in msg.text.entities if e.custom_emoji_id}
    ids.update({e.custom_emoji_id for msg in msgs if msg.caption_entities for e in msg.caption_entities if e.custom_emoji_id})
    ids = list(ids)
    orig_ids = list(ids)

    # Query stickers 200 ids at a time
    stickers: list[Sticker] = []
    while ids:
        stickers += await app.get_custom_emoji_stickers(ids[:200])
        ids = ids[200:]

    # Download stickers
    for id, s in zip(orig_ids, stickers):
        ext = guess_ext(app, FileId.decode(s.file_id).file_type, s.mime_type)
        op = (await download_media(app, s, path / "emoji", f'{id}{ext}')).absolute().relative_to(path.absolute())

        # Replace sticker paths
        for r in results:
            if "text" in r:
                r['text'] = r['text'].replace(f'<i class="custom-emoji" emoji-src="emoji/{id}">',
                                              f'<i class="custom-emoji" emoji-src="{op}">')


def get_post_ids(p: dict) -> set[int]:
    """
    Get all message IDs associated with a post (including media group items)
    """
    ids = {p['id']}
    for item in (p.get('images') or []) + (p.get('files') or []):
        url = item.get('url', '')
        stem = Path(url).stem
        if stem.isdigit():
            ids.add(int(stem))
    return ids


async def process_chat(chat_id: int, path: Path, export: dict, full: bool = False, overlap: int | None = None):
    chat: Chat = await app.get_chat(chat_id)
    printc(f"&aChat obtained. Chat name: {chat.title} | Type: {chat.type} | ID: {chat.id}")

    is_full = full or export.get('full', False)
    overlap_count = overlap if overlap is not None else export.get('overlap', 20)

    existing_posts: list[dict] = []
    posts_file = path / "posts.json"
    if not is_full and posts_file.is_file():
        try:
            with open(posts_file, "r", encoding="utf-8") as f:
                existing_posts = json.load(f)
        except Exception as e:
            print(f"Warning: Failed to load existing {posts_file} ({e}), performing full crawl...")
            existing_posts = []

    preserved_posts: list[dict] = []
    if existing_posts:
        # Determine overlap cutoff point
        idx = max(0, len(existing_posts) - overlap_count)
        # Avoid splitting a media group across preserved and target posts
        while idx > 0 and existing_posts[idx].get('media_group_id') and existing_posts[idx]['media_group_id'] == existing_posts[idx - 1].get('media_group_id'):
            idx -= 1

        preserved_posts = existing_posts[:idx]
        target_posts = existing_posts[idx:]
        start_idx = min(min(get_post_ids(p)) for p in target_posts)
        printc(f"&bIncremental crawl mode: Preserving {len(preserved_posts)} older posts, re-checking from post ID #{start_idx} (overlap: {len(target_posts)} posts)")
    else:
        start_idx = 1
        if is_full:
            printc("&eFull crawl mode: crawling from message ID #1...")
        else:
            printc("&eNo existing posts found: starting initial crawl from message ID #1...")

    # Crawl 200 messages each request
    print(f"Crawling channel posts (starting from ID #{start_idx})...")
    msgs = []
    curr_idx = start_idx
    batch_size = 200

    while True:
        end_idx = curr_idx + batch_size
        additional_msgs = await app.get_messages(chat.id, range(curr_idx, end_idx))
        additional_msgs = [m for m in additional_msgs if not m.empty]
        msgs += additional_msgs
        print(f"> {len(msgs)} total messages... (up to ID #{end_idx - 1})")

        if not additional_msgs:
            print("> All messages in batch are empty, we're done.")
            break

        # In incremental mode, if the batch messages stopped well before the end of the batch,
        # we have reached the end of the channel and can stop early without waiting for another empty batch.
        max_batch_id = max(m.id for m in additional_msgs)
        if not is_full and (end_idx - 1) - max_batch_id > 20:
            print(f"> Reached end of channel (last message ID: #{max_batch_id}).")
            break

        curr_idx = end_idx

    results = [await process_message(m, path, export) for m in msgs]
    await download_custom_emojis(msgs, results, path)

    # Group new messages, resolving replies using preserved posts
    new_posts = group_msgs(results, lookup_posts=preserved_posts)

    # Merge preserved posts with new posts
    new_post_ids = {p['id'] for p in new_posts}
    final_posts = [p for p in preserved_posts if p['id'] not in new_post_ids] + new_posts
    final_posts.sort(key=lambda x: x['id'])

    write(path / "posts.json", json_stringify(final_posts, indent=2))
    write(path / "index.html", HTML.replace("$$POSTS_DATA$$", json_stringify(final_posts)))

    if 'rss' in export:
        print("Exporting RSS feed...")
        posts_to_feed(path, FeedMeta(**export['rss']))

    printc(f"&aDone! Saved to {path / 'posts.json'} ({len(final_posts)} total posts)")


async def run_app(full: bool = False, overlap: int | None = None):
    me: User = await app.get_me()
    printc(f"&aLogin success! ID: {me.id} | is_bot: {me.is_bot}")
    for export in cfg.exports:
        await process_chat(int(export["chat_id"]), Path(export["path"]), export, full=full, overlap=overlap)


cfg: Config
app: Client


def run():
    global app, cfg
    parser = argparse.ArgumentParser("Telegram Channel Message to Public API Crawler")
    parser.add_argument("config", help="Config path", nargs="?", default="config.toml")
    parser.add_argument("--full", action="store_true", help="Perform a full crawl from the beginning instead of incremental")
    parser.add_argument("--overlap", type=int, default=None, help="Number of recent posts to overlap during incremental crawl (default: 20)")
    args = parser.parse_args()
    cfg = load_config(args.config)

    app = Client("Bot", cfg.api_id or 2048, cfg.api_hash or "b18441a1ff607e10a989891a5462e627",
                 **(dict(bot_token=cfg.bot_token) if cfg.bot_token else {}))

    with app:
        app.loop.run_until_complete(run_app(full=args.full, overlap=args.overlap))
