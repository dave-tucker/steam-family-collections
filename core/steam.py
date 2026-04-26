import time

import requests

_OWNED_GAMES = "https://api.steampowered.com/IPlayerService/GetOwnedGames/v1/"
_APP_DETAILS = "https://store.steampowered.com/api/appdetails"
_STEAM_KEY_TO_SCHEME = {"pegi": "pegi", "pegifit": "pegi", "pegi_bbfc": "bbfc"}


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


def fetch_ratings_from_steam(appid: int) -> dict[str, str]:
    """Return a dict of scheme → raw rating string from the Steam store API.

    Uses the GB storefront (PEGI/BBFC territory). Returns an empty dict if
    no ratings are found or the request fails.
    """
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
        return {}

    ratings = data.get("data", {}).get("ratings", {})
    result: dict[str, str] = {}
    for key, scheme in _STEAM_KEY_TO_SCHEME.items():
        entry = ratings.get(key)
        if entry and isinstance(entry, dict):
            raw = str(entry.get("rating", "")).strip()
            digits = "".join(c for c in raw if c.isdigit())
            if digits and scheme not in result:
                result[scheme] = digits
    return result
