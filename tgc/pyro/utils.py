import base64

FILENAME_BLACKLIST = [
    # Unix and Windows
    "/",

    # Windows only
    "<", ">", ":", '"', "\\", "|", "?", "*", "\0",
    "CON", "PRN", "AUX", "NUL",
    "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
    "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
    
    # Just for extra safety
    "~"
]

FILENAME_REPLACE = {c: f"%{base64.b64encode(c.encode()).decode().replace('=', '')}" for c in FILENAME_BLACKLIST}


def escape_filename(fn: str) -> str:
    fn = fn.replace("%", "[ PeRcEnT EsCaPe owo ]")

    for c, r in FILENAME_REPLACE.items():
        fn = fn.replace(c, r)

    fn = fn.replace("[ PeRcEnT EsCaPe owo ]", "%%")
    return fn


def unescape_filename(fn: str) -> str:
    fn = fn.replace("%%", "[ PeRcEnT EsCaPe owo ]")

    for c, r in FILENAME_REPLACE.items():
        fn = fn.replace(r, c)

    fn = fn.replace("[ PeRcEnT EsCaPe owo ]", "%")
    return fn
