import asyncio
import mimetypes
from pathlib import Path
from typing import Any

from hypy_utils import ensure_dir
from hypy_utils.file_utils import escape_filename
from telethon import TelegramClient
from telethon.errors import FloodWaitError
from telethon.tl.custom.file import File
from telethon.tl.custom.message import Message


def guess_ext(mime_type: str | None, fallback: str = ".unknown") -> str:
    if not mime_type:
        return fallback
    return mimetypes.guess_extension(mime_type) or fallback


def has_media(message: Message | Any) -> Any | None:
    if isinstance(message, Message):
        return message.media
    return message


def get_file_name(message: Message | Any) -> str:
    if isinstance(message, Message):
        f: File | None = message.file
        if f and f.name:
            return escape_filename(f.name)
        ext = getattr(f, "ext", None) or guess_ext(getattr(f, "mime_type", None))
        return escape_filename(f"{message.id}{ext}")

    file_name = getattr(message, "name", None) or getattr(message, "file_name", None)
    mime_type = getattr(message, "mime_type", None)
    if file_name:
        return escape_filename(file_name)
    file_id = getattr(message, "id", "file")
    return escape_filename(f"{file_id}{guess_ext(mime_type)}")


async def download_media(
        client: TelegramClient,
        message: Message | Any,
        directory: str | Path = "media",
        fname: str | None = None,
        max_file_size: int = 0,
        thumb: int | None = None
) -> Path | None:
    directory: Path = ensure_dir(directory)
    media = has_media(message)
    if media is None:
        return None

    fsize = getattr(getattr(message, "file", None), "size", None) or getattr(message, "size", 0)
    if max_file_size and fsize and fsize > max_file_size:
        print(f"Skipped {fname} because of file size limit ({fsize} > {max_file_size})")
        return None

    file_name = fname or get_file_name(message)
    p = directory / file_name
    if p.exists():
        return p

    print(f"Downloading {p.name}...")
    while True:
        try:
            out = await client.download_media(message, file=str(p), thumb=thumb)
            return Path(out) if out else None
        except FloodWaitError as e:
            print(f"Sleeping for {e.seconds} seconds...")
            await asyncio.sleep(e.seconds)


async def download_media_urlsafe(
        client: TelegramClient,
        message: Message,
        directory: str | Path = "media",
        max_file_size: int = 0
) -> tuple[Path | None, str]:
    """
    Download media into a renamed file

    :return: Renamed file path, original file name
    """
    file_name = get_file_name(message)
    renamed = str(message.id) + Path(file_name).suffix
    return await download_media(client, message, directory, renamed, max_file_size), file_name
