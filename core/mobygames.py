import re
import time
from collections import Counter

import requests

_SEARCH_URL = "https://api.mobygames.com/v1/games"
_PLATFORMS_URL = "https://api.mobygames.com/v1/games/{game_id}/platforms"
_PLATFORM_URL = "https://api.mobygames.com/v1/games/{game_id}/platforms/{platform_id}"
_VALID_PEGI = (3, 7, 12, 16, 18)

# Title normalisation applied before every MobyGames search.
# Each pattern is stripped in order; the edition regex removes the matched
# keyword AND everything that follows it (edition info always trails the title).
_TITLE_CLEANERS = [
    re.compile(r"[™®©]"),  # trademark / copyright symbols
    re.compile(r"\s*\((TM|R)\)", re.IGNORECASE),  # (TM) / (R) as ASCII text
    re.compile(r"\s*\(\d{4}\)"),  # bare year: (2013)
    re.compile(  # edition / remaster qualifiers
        r"[\s:–\-]*\b(?:(?:A|An|The)\s+)?("  # optional leading article
        r"Game of the Year( Edition)?"
        r"|GOTY( Edition)?"
        r"|Definitive Edition"
        r"|Enhanced Edition"
        r"|Complete Edition"
        r"|Ultimate Edition"
        r"|Deluxe Edition"
        r"|Special Edition"
        r"|Extended Edition"
        r"|Gold Edition"
        r"|Anniversary Edition"
        r"|Classic Edition"
        r"|Collector'?s Edition"
        r"|Director'?s Cut"
        r"|Remastered"
        r"|Remaster"
        r"|Redux"
        r"|HD Remaster(ed)?"
        r"|HD Edition"
        r"|HD"
        r"|4K Edition"
        r"|Steam Edition"
        r"|PC Edition"
        r"|VR Edition"
        r")\b.*$",
        re.IGNORECASE,
    ),
    re.compile(r"[!?]+"),  # exclamation / question marks
    re.compile(r":"),  # colons (subtitle separator)
    re.compile(r"\s{2,}"),  # collapse runs of whitespace
]


def clean_title(title: str) -> str:
    """Strip Steam-specific noise from a title before searching MobyGames."""
    for pat in _TITLE_CLEANERS[:-1]:
        title = pat.sub("", title)
    title = _TITLE_CLEANERS[-1].sub(" ", title)  # collapse whitespace → single space
    return title.strip(" \t-–:,")


def search_games(title: str, api_key: str) -> list[dict]:
    """Search by title. Returns candidate game dicts (each has game_id + platforms).

    If the full cleaned title returns nothing and contains a ' - ' subtitle
    separator, retries with just the part before the dash (MobyGames AKA
    matching handles the rest).
    """
    cleaned = clean_title(title)
    results = _search(cleaned, api_key)
    if not results and " - " in cleaned:
        shorter = cleaned.split(" - ")[0].strip(" \t-–:,")
        if shorter and shorter != cleaned:
            results = _search(shorter, api_key)
    return results


def _search(title: str, api_key: str) -> list[dict]:
    resp = _get_with_backoff(
        _SEARCH_URL,
        {"title": title, "api_key": api_key, "limit": 10},
    )
    return resp.json().get("games", [])


def fetch_pegi_for_moby_id(moby_id: int, api_key: str) -> int | None:
    """Fetch PEGI rating for a known MobyGames game ID.

    Walks every platform release, collects PEGI ratings, and returns the
    most common one (ties broken by the lowest / most permissive value).
    """
    resp = _get_with_backoff(
        _PLATFORMS_URL.format(game_id=moby_id),
        {"api_key": api_key},
    )
    platforms = resp.json().get("platforms", [])

    values: list[int] = []
    for plat in platforms:
        pid = plat.get("platform_id")
        if not pid:
            continue
        time.sleep(1)
        try:
            r = _get_with_backoff(
                _PLATFORM_URL.format(game_id=moby_id, platform_id=pid),
                {"api_key": api_key},
            )
            for rating in r.json().get("ratings", []):
                val = _parse_pegi(rating)
                if val is not None:
                    values.append(val)
        except Exception:
            pass

    if not values:
        return None

    counts = Counter(values)
    return min(counts, key=lambda v: (-counts[v], v))


def _parse_pegi(rating: dict) -> int | None:
    """Extract a snapped PEGI integer from a MobyGames rating dict, or None."""
    sys_name = str(rating.get("rating_system_name", "")).upper()
    if "PEGI" not in sys_name:
        return None
    raw = str(rating.get("rating_name", ""))
    digits = "".join(c for c in raw if c.isdigit())
    if not digits:
        return None
    val = int(digits)
    for bracket in _VALID_PEGI:
        if val <= bracket:
            return bracket
    return None


def _get_with_backoff(url: str, params: dict, retries: int = 4) -> requests.Response:
    backoff = 10
    for _ in range(retries):
        resp = requests.get(url, params=params, timeout=30)
        if resp.status_code == 429:
            time.sleep(backoff)
            backoff = min(backoff * 2, 120)
            continue
        resp.raise_for_status()
        return resp
    resp.raise_for_status()
    return resp  # unreachable


def candidate_summary(game: dict) -> str:
    title = game.get("title", "Unknown")
    year = (game.get("first_release_date") or "")[:4] or "?"
    platforms = ", ".join(p.get("platform_name", "") for p in game.get("platforms", [])[:3])
    return f"{title} ({year}) — {platforms}"
