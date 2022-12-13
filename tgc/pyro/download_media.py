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

from pathlib import Path
from typing import Callable

from hypy_utils import ensure_dir
from pyrogram import types, Client
from pyrogram.file_id import FileId, FileType, PHOTO_TYPES


def guess_ext(client: Client, file_type: int, mime_type: str) -> str:
    guessed_extension = client.guess_extension(mime_type)

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


async def download_media(
        client: Client,
        message: types.Message,
        directory: str | Path = "media",
        progress: Callable = None,
        progress_args: tuple = ()
) -> Path:
    directory: Path = ensure_dir(directory)

    available_media = ("audio", "document", "photo", "sticker", "animation", "video", "voice", "video_note",
                       "new_chat_photo")

    if isinstance(message, types.Message):
        for kind in available_media:
            media = getattr(message, kind, None)

            if media is not None:
                break
        else:
            raise ValueError("This message doesn't contain any downloadable media")
    else:
        media = message

    if isinstance(media, str):
        file_id_str = media
    else:
        file_id_str = media.file_id

    file_id_obj = FileId.decode(file_id_str)
    file_type = file_id_obj.file_type

    file_size = getattr(media, "file_size", 0)
    mime_type = getattr(media, "mime_type", "")
    date = getattr(media, "date", None)

    file_name = getattr(media, "file_name")

    if not file_name:
        file_name = f"{FileType(file_type).name.lower()}"
        if date:
            file_name += f"_{date.strftime('%Y-%m-%d_%H-%M-%S')}"
        file_name += guess_ext(client, file_type, mime_type)

    p = directory / file_name
    if p.exists():
        return p

    print(f"Downloading {p}...")

    return Path(await client.handle_download(
        (file_id_obj, directory, file_name, False, file_size, progress, progress_args)
    ))
