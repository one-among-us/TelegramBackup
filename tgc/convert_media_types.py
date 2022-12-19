import os
import zlib
from pathlib import Path
from shutil import which
from subprocess import check_call

from hypy_utils import printc


SCRIPT_PATH = Path(__file__).parent

NODE_BIN_PATHS: list[Path] = [
    SCRIPT_PATH / 'node_modules/.bin',
    Path('node_modules/.bin'),
    Path.home() / 'node_modules/.bin',
    Path.home() / '.config/yarn/global/node_modules/.bin',
    Path('/usr/local/bin'),
    Path('/usr/bin')
]


def find_node_bin(name: str, pkg_name: str) -> Path:
    # Find bin path
    path = which(name)
    if path and os.path.isfile(path):
        return Path(path)

    for bin in NODE_BIN_PATHS:
        if (bin / name).is_file():
            return bin / name

    printc(f"&cError! Cannot find node executable {name}. \n"
           f"Make sure to install it using 'yarn global add {pkg_name}'")
    exit(3)


def tgs_to_apng(tgs: str | Path) -> Path:
    """
    Convert .tgs vector animation into .apng bitmap animation

    :param tgs: TGS file
    :return: Converted path (str)
    """
    tgs = Path(tgs)
    out = tgs.with_suffix(".apng")

    if not out.is_file():
        # Decompress to json
        json = tgs.with_suffix(".json")
        json.write_bytes(zlib.decompress(tgs.read_bytes(), 15 + 32))

        # Convert json to apng
        check_call([find_node_bin("puppeteer-lottie", "puppeteer-lottie-cli"), '-i', json, '-o', out])

        # Delete json
        os.remove(json)

    return out


def webm_to_apng(webm: str, p: Path) -> str:
    """
    Convert .webm contained animation into .apng bitmap animation

    :param webm: Webm file
    :param p: Output path
    :return: Converted path (str)
    """
    out = str(Path(webm).with_suffix(".apng"))

    if not (p / out).is_file():
        # Convert webm to apng using ffmpeg
        cmd = ['ffmpeg', '-c:v', 'libvpx-vp9',
               # '-pix_fmt', 'yuva420p',
               '-i', str(p / webm),
               '-plays', '0',
               str(p / out)]
        print(' '.join(cmd))
        check_call(cmd)

    return out
