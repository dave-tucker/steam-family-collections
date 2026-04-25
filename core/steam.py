import time

import requests

_OWNED_GAMES = "https://api.steampowered.com/IPlayerService/GetOwnedGames/v1/"
_APP_DETAILS = "https://store.steampowered.com/api/appdetails"
_PEGI_KEYS = ("pegi", "pegifit", "pegi_bbfc")


def fetch_library(api_key: str, steam_id: str) -> list[dict]:
    resp = requests.get(
        _OWNED_GAMES,
        params={
            "key": api_key,
            "steamid": steam_id,
            "include_appinfo": 1,
            "format": "json",
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json().get("response", {}).get("games", [])


def fetch_pegi_from_steam(appid: int) -> int | None:
    backoff = 60
    while True:
        resp = requests.get(
            _APP_DETAILS,
            params={"appids": appid, "cc": "gb", "l": "en"},
            timeout=30,
        )
        if resp.status_code == 429:
            time.sleep(backoff)
            backoff = min(backoff * 2, 300)
            continue
        resp.raise_for_status()
        break

    data = resp.json().get(str(appid), {})
    if not data.get("success"):
        return None

    ratings = data.get("data", {}).get("ratings", {})
    for key in _PEGI_KEYS:
        entry = ratings.get(key)
        if entry and isinstance(entry, dict):
            raw = str(entry.get("rating", ""))
            digits = "".join(c for c in raw if c.isdigit())
            if digits:
                return int(digits)
    return None
