"""Record one list page and one detail record per family into tests/fixtures."""

from __future__ import annotations

import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from scwiki import __version__
from scwiki.core.families import FAMILIES

BASE = "https://api.star-citizen.wiki/api"
OUT = Path(__file__).resolve().parents[1] / "tests" / "fixtures"
HEADERS = {"Accept": "application/json", "User-Agent": f"scwiki/{__version__} fixtures"}

EXTRA = {
    "game-versions.default": "game-versions/default",
    "search": "search?filter%5Bquery%5D=avenger",
    "stats.latest": "stats/latest",
    "vehicles.filters": "vehicles/filters",
    "locations.positions": "locations/positions",
}


def get(url: str) -> Any:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as fh:
        return json.load(fh)


def write(name: str, payload: Any) -> None:
    (OUT / f"{name}.json").write_text(json.dumps(payload, indent=1) + "\n")


def identifier_of(row: dict[str, Any]) -> str:
    for key in ("slug", "uuid", "code", "id", "name"):
        if row.get(key) is not None:
            return str(row[key])
    raise KeyError("no identifier in row")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for fam in FAMILIES.values():
        stem = fam.path.replace("/", "-")
        listing = get(f"{BASE}/{fam.path}?page%5Bsize%5D=2")
        write(f"{stem}.list", listing)
        if fam.name == "stats":
            continue
        ident = identifier_of(listing["data"][0])
        detail = get(f"{BASE}/{fam.path}/{urllib.parse.quote(ident, safe='')}")
        write(f"{stem}.detail", detail)
        print(f"{fam.name}: {ident}")
        time.sleep(0.3)
    for name, path in EXTRA.items():
        payload = get(f"{BASE}/{path}")
        if name == "locations.positions":
            payload["data"] = payload["data"][:20]
        write(name, payload)
        print(name)


if __name__ == "__main__":
    main()
