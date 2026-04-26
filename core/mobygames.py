import re
import time
from collections import Counter

import requests

from core.ratings import normalize_scheme

_SEARCH_URL = "https://api.mobygames.com/v1/games"
_PLATFORMS_URL = "https://api.mobygames.com/v1/games/{game_id}/platforms"
_PLATFORM_URL = "https://api.mobygames.com/v1/games/{game_id}/platforms/{platform_id}"

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


# MobyGames platform IDs for desktop PC platforms
_PC_PLATFORM_IDS = frozenset([1, 3, 74])  # Linux, Windows, Macintosh
_SEARCH_LIMIT = 20


def _filter_pc(results: list[dict]) -> list[dict]:
    """Return only games that have at least one PC/Mac/Linux release."""
    return [
        g
        for g in results
        if any(p["platform_id"] in _PC_PLATFORM_IDS for p in g.get("platforms", []))
    ]


def search_games(title: str, api_key: str, *, raw: bool = False) -> list[dict]:
    """Search by title. Returns candidate game dicts (each has game_id + platforms).

    When raw=True the title is passed to the API as-is (no cleaning or retries).
    Results are filtered to games with a PC/Mac/Linux release; if that leaves
    nothing, all results are returned so the user still has something to pick from.

    Retry strategy (raw=False) when the full cleaned title returns nothing:
    1. If cleaned title contains ' - ', retry with the part before the dash.
    2. If original title contains ':', retry with the part before the colon
       (colon stripping can break MobyGames search for subtitled games like
       'Half-Life 2: Deathmatch').
    """
    if raw:
        return _search_filtered(title, api_key)

    cleaned = clean_title(title)
    results = _search_filtered(cleaned, api_key)
    if not results and " - " in cleaned:
        shorter = cleaned.split(" - ")[0].strip(" \t-–:,")
        if shorter and shorter != cleaned:
            results = _search_filtered(shorter, api_key)
    if not results and ":" in title:
        pre_colon = clean_title(title.split(":")[0])
        if pre_colon and pre_colon != cleaned:
            results = _search_filtered(pre_colon, api_key)
    return results


def _search_filtered(title: str, api_key: str) -> list[dict]:
    results = _search(title, api_key)
    pc_only = _filter_pc(results)
    return pc_only if pc_only else results


def _search(title: str, api_key: str) -> list[dict]:
    resp = _get_with_backoff(
        _SEARCH_URL,
        {"title": title, "api_key": api_key, "limit": _SEARCH_LIMIT},
    )
    return resp.json().get("games", [])


def fetch_ratings_for_moby_id(moby_id: int, api_key: str) -> dict[str, str]:
    """Fetch all ratings for a known MobyGames game ID.

    Walks every platform release and collects ratings for all known schemes.
    Returns a dict of scheme → most common raw value across platforms.
    """
    resp = _get_with_backoff(
        _PLATFORMS_URL.format(game_id=moby_id),
        {"api_key": api_key},
    )
    platforms = resp.json().get("platforms", [])

    scheme_values: dict[str, list[str]] = {}
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
                result = _parse_rating(rating)
                if result is not None:
                    scheme, value = result
                    scheme_values.setdefault(scheme, []).append(value)
        except Exception:
            pass

    return {scheme: Counter(vals).most_common(1)[0][0] for scheme, vals in scheme_values.items()}


def _parse_rating(rating: dict) -> tuple[str, str] | None:
    """Return (scheme, raw_value) from a MobyGames rating dict, or None."""
    sys_name = str(rating.get("rating_system_name", ""))
    scheme = normalize_scheme(sys_name)
    if scheme is None:
        return None
    raw = str(rating.get("rating_name", "")).strip()
    if not raw:
        return None
    return scheme, raw


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
