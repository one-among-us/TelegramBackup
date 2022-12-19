#  Pyrogram - Telegram MTProto API Client Library for Python
#  Copyright (C) 2017-present Dan <https://github.com/delivrance>
#
#  This file is part of Pyrogram.
#
#  Pyrogram is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Lesser General Public License as published
#  by the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  Pyrogram is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public License
#  along with Pyrogram.  If not, see <http://www.gnu.org/licenses/>.
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Callable, Any

from hypy_utils import ensure_dir, md5
from hypy_utils.file_utils import escape_filename
from pyrogram import types, Client
from pyrogram.file_id import FileId, FileType, PHOTO_TYPES
from pyrogram.types import Message


def guess_ext(client: Client, file_type: int, mime_type: str | None) -> str:
    guessed_extension = client.guess_extension(mime_type) if mime_type else None

    if file_type in PHOTO_TYPES:
        return ".jpg"
    elif file_type == FileType.VOICE:
        return guessed_extension or ".ogg"
    elif file_type in (FileType.VIDEO, FileType.ANIMATION, FileType.VIDEO_NOTE):
        return guessed_extension or ".mp4"
    elif file_type == FileType.DOCUMENT:
        return guessed_extension or ".zip"
    elif file_type == FileType.STICKER:
        return guessed_extension or ".webp"
    elif file_type == FileType.AUDIO:
        return guessed_extension or ".mp3"
    else:
        return ".unknown"


def has_media(message: Message) -> Any | None:
    available_media = ("audio", "document", "photo", "sticker", "animation", "video", "voice", "video_note",
                       "new_chat_photo")

    if isinstance(message, types.Message):
        for kind in available_media:
            media = getattr(message, kind, None)

            if media is not None:
                break
        else:
            return None
    else:
        media = message

    return media


def get_file_name(client: Client, message: Message) -> tuple[str, FileId]:
    """
    Guess a file name of a message media

    :param client: Client
    :param message: Message or media
    :return: File name, file id object
    """
    media = has_media(message)

    if isinstance(media, str):
        file_id_str = media
    else:
        file_id_str = media.file_id

    file_id_obj = FileId.decode(file_id_str)
    file_type = file_id_obj.file_type

    mime_type = getattr(media, "mime_type", "")
    date = getattr(media, "date", None)

    file_name = getattr(media, "file_name", None)

    if not file_name:
        file_name = f"{FileType(file_type).name.lower()}"
        if date:
            file_name += f"_{date.strftime('%Y-%m-%d_%H-%M-%S')}"
        file_name += guess_ext(client, file_type, mime_type)
    file_name = escape_filename(file_name)

    return file_name, file_id_obj


async def download_media(
        client: Client,
        message: types.Message,
        directory: str | Path = "media",
        fname: str | None = None,
        progress: Callable = None,
        progress_args: tuple = ()
) -> Path:
    directory: Path = ensure_dir(directory)

    media = has_media(message)

    file_name, file_id_obj = get_file_name(client, message)
    file_name = fname or file_name

    p = directory / file_name
    if p.exists():
        return p

    print(f"Downloading {p.name}...")

    return Path(await client.handle_download(
        (file_id_obj, directory, file_name, False, getattr(media, "file_size", 0), progress, progress_args)
    ))


async def download_media_urlsafe(
        client: Client,
        message: types.Message,
        directory: str | Path = "media",
        fname: str | None = None,
        progress: Callable = None,
        progress_args: tuple = ()
) -> tuple[Path, str]:
    """
    Download media into a renamed file

    :return: Renamed file path, original file name
    """
    file_name, file_id_obj = get_file_name(client, message)
    renamed = str(message.id) + Path(file_name).suffix
    return await download_media(client, message, directory, renamed, progress, progress_args), file_name
