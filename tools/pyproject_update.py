# Requires johnnydep
import tomllib
from pathlib import Path

from johnnydep.lib import JohnnyDist
from tabulate import tabulate


class safelist(list):
    def get(self, index, default=None):
        try:
            return self.__getitem__(index)
        except IndexError:
            return default


if __name__ == '__main__':
    deps: list[str] = tomllib.loads(Path("pyproject.toml").read_text())['project']['dependencies']
    deps: list[safelist[str]] = [safelist(d.replace(">=", "==").replace("~=", "==").split("==")) for d in deps]
    deps: list[tuple[str, str, str]] = [(t[0], t.get(1, None), JohnnyDist(t[0]).version_latest) for t in deps]

    print(tabulate(deps))
