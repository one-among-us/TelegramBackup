import asyncio
import os
import subprocess
import zlib
from pathlib import Path
from pyrogram import Client, raw
from pyrogram.types import Sticker
from tgc.convert_media_types import tgs_to_apng

# Cache sticker sets in memory so we only query Telegram once per emoji type
_DICE_SETS: dict[str, list] = {}

EMOJI_NAME_MAP = {
    "🎲": "die",
    "🎯": "dart",
    "🏀": "basketball",
    "⚽": "football",
    "🎳": "bowling",
    "🎰": "slot"
}


async def _download_sticker_json(app: Client, doc: raw.types.Document, tgs_path: Path) -> Path:
    if not tgs_path.is_file():
        st = await Sticker._parse(app, doc, {type(i): i for i in doc.attributes})
        await app.download_media(st.file_id, file_name=str(tgs_path))
    json_path = tgs_path.with_suffix(".json")
    if not json_path.is_file():
        json_path.write_bytes(zlib.decompress(tgs_path.read_bytes(), 15 + 32))
    return json_path


async def download_dice_animation(app: Client, emoji: str, value: int, media_path: Path) -> Path | None:
    """
    Download and convert Telegram's official animated dice sticker for an outcome value.
    Returns path to converted .apng file.
    """
    emoji_name = EMOJI_NAME_MAP.get(emoji, "dice")
    apng_file = media_path / f"dice_{emoji_name}_{value}.apng"
    if apng_file.is_file():
        return apng_file

    try:
        if emoji not in _DICE_SETS:
            r = await app.invoke(raw.functions.messages.GetStickerSet(
                stickerset=raw.types.InputStickerSetDice(emoticon=emoji),
                hash=0
            ))
            _DICE_SETS[emoji] = r.documents

        docs = _DICE_SETS[emoji]
        if not docs:
            return None

        if emoji == "🎰":
            # Multi-layer slot machine
            val = max(0, value - 1)
            reel_left = val & 3
            reel_center = (val >> 2) & 3
            reel_right = (val >> 4) & 3
            # Visual stacking order from bottom to top:
            # 1. Background: layer 0 (and winning background layer 1 if win)
            # 2. Reels: left, center, right
            # 3. Machine frame & lever: layer 2 (masks the reels so top/bottom items are hidden)
            layer_indices = [0, 3 + reel_left, 9 + reel_center, 15 + reel_right, 2]
            if val == 63:  # 777 win
                layer_indices.insert(1, 1)

            json_files: list[Path] = []
            for idx in layer_indices:
                if idx < len(docs):
                    tgs_p = media_path / f"slot_layer_{idx}.tgs"
                    jp = await _download_sticker_json(app, docs[idx], tgs_p)
                    json_files.append(jp)

            multi_script = Path(__file__).parent / "render_multi_lottie.js"
            cmd = ["node", str(multi_script), str(apng_file)] + [str(p) for p in json_files]
            subprocess.check_call(cmd)

            # Cleanup temp layer jsons
            for jp in json_files:
                if jp.is_file():
                    os.remove(jp)

            if apng_file.is_file():
                return apng_file
            return None

        if value >= len(docs):
            return None

        doc = docs[value]
        st = await Sticker._parse(app, doc, {type(i): i for i in doc.attributes})
        tgs_file = media_path / f"dice_{emoji_name}_{value}.tgs"
        if not tgs_file.is_file():
            await app.download_media(st.file_id, file_name=str(tgs_file))

        res = tgs_to_apng(tgs_file)
        if res and Path(res).suffix == ".apng":
            return Path(res)
        return None
    except Exception as e:
        print(f"Warning: Failed to download dice animation for {emoji} {value}: {e}")
        return None
