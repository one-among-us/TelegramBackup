import os
from dataclasses import dataclass
from pathlib import Path

import toml
from hypy_utils import printc


@dataclass
class Config:
    api_id: int
    api_hash: str
    bot_token: str
    exports: list[dict]


def load_config(path: str = "config.toml") -> Config:
    if os.getenv('tgc_config'):
        return Config(**toml.loads(os.getenv('tgc_config')))

    fp = os.getenv('tgc_config_path')

    if fp is None or not os.path.isfile(fp):
        fp = path
    if fp is None or not os.path.isfile(fp):
        fp = Path.home() / ".config" / "tgc" / "config.toml"

    fp = Path(fp)

    if not fp.is_file():
        printc(f"&cConfig file not found in either {path} or {fp} \nPlease put your configuration in the path")
        exit(3)

    return Config(**toml.loads(fp.read_text()))
