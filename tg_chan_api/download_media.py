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

import asyncio
import os
from datetime import datetime
from pathlib import Path
from typing import Union, Optional, Callable, BinaryIO

import pyrogram
from pyrogram import types
from pyrogram.file_id import FileId, FileType, PHOTO_TYPES


async def download_media(
        client: pyrogram.Client,
        message: types.Message,
        directory: str = "media",
        progress: Callable = None,
        progress_args: tuple = ()
) -> Path:
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
    media_file_name = getattr(media, "file_name", "")
    file_size = getattr(media, "file_size", 0)
    mime_type = getattr(media, "mime_type", "")
    date = getattr(media, "date", None)

    file_name = media_file_name or ""

    if not file_name:
        guessed_extension = client.guess_extension(mime_type)

        if file_type in PHOTO_TYPES:
            extension = ".jpg"
        elif file_type == FileType.VOICE:
            extension = guessed_extension or ".ogg"
        elif file_type in (FileType.VIDEO, FileType.ANIMATION, FileType.VIDEO_NOTE):
            extension = guessed_extension or ".mp4"
        elif file_type == FileType.DOCUMENT:
            extension = guessed_extension or ".zip"
        elif file_type == FileType.STICKER:
            extension = guessed_extension or ".webp"
        elif file_type == FileType.AUDIO:
            extension = guessed_extension or ".mp3"
        else:
            extension = ".unknown"

        file_name = f"{FileType(file_id_obj.file_type).name.lower()}_{date.strftime('%Y-%m-%d_%H-%M-%S')}{extension}"

    p = Path(directory) / file_name
    if p.exists():
        return p

    print(f"Downloading {p}...")

    downloader = client.handle_download(
        (file_id_obj, directory, file_name, False, file_size, progress, progress_args)
    )

    return Path(await downloader)
