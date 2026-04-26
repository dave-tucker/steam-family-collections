from __future__ import annotations

_DEFAULT_PREFERENCE = ["bbfc", "pegi", "usk", "esrb"]

_DEFAULT_MAP: dict[str, dict[str, int | None]] = {
    "esrb": {
        "EC": 3,
        "E": 3,
        "E10+": 7,
        "T": 12,
        "M": 16,
        "AO": 18,
        "RP": None,
    },
    "bbfc": {
        "U": 0,
        "PG": 5,
        "12A": 12,
        "12": 12,
        "15": 15,
        "18": 18,
        "R18": 18,
    },
    "classind": {
        "L": 0,
        "10": 10,
        "12": 12,
        "14": 14,
        "16": 16,
        "18": 18,
    },
}

# Ordered: first match wins when a system name contains multiple keywords.
_SCHEME_ALIASES = [
    ("BBFC", "bbfc"),
    ("PEGI", "pegi"),
    ("ESRB", "esrb"),
    ("USK", "usk"),
    ("CLASSIND", "classind"),
    ("APPLE", "apple"),
    ("GRB", "grb"),
    ("OFLC", "oflc"),
    ("ACB", "acb"),
    ("CERO", "cero"),
]


def normalize_scheme(rating_system_name: str) -> str | None:
    """Map a MobyGames rating system name to a short scheme key, or None."""
    upper = rating_system_name.upper()
    for fragment, key in _SCHEME_ALIASES:
        if fragment in upper:
            return key
    return None


def apply_map(
    scheme: str, raw_value: str, rating_map: dict[str, dict[str, int | None]]
) -> int | None:
    """Convert a raw rating string to a numeric age value.

    Tries the config map first (exact match, then first token before whitespace/dash).
    Falls back to extracting digits from the raw string.
    Returns None if the value cannot be resolved to a number.
    """
    scheme_map = rating_map.get(scheme, {})
    if scheme_map:
        if raw_value in scheme_map:
            return scheme_map[raw_value]
        # Handle "T - Teen 13+" style values: match on first token
        first_token = raw_value.split()[0].rstrip("-")
        if first_token in scheme_map:
            result = scheme_map[first_token]
            return result if result is not None else None

    digits = "".join(c for c in raw_value if c.isdigit())
    if digits:
        return int(digits)
    return None


def select_rating(
    ratings: dict[str, str],
    preference: list[str],
    rating_map: dict[str, dict[str, int | None]],
) -> tuple[str, int] | None:
    """Pick the best (scheme, age) from a raw ratings dict.

    Tries schemes in preference order, then falls back to the rounded average
    of all successfully mapped values. Returns None if nothing resolves.
    """
    if not ratings:
        return None

    for scheme in preference:
        raw = ratings.get(scheme)
        if raw is None:
            continue
        age = apply_map(scheme, raw, rating_map)
        if age is not None:
            return scheme, age

    values: list[int] = []
    for scheme, raw in ratings.items():
        age = apply_map(scheme, raw, rating_map)
        if age is not None:
            values.append(age)
    if values:
        return "average", round(sum(values) / len(values))

    return None


def get_preference(config: dict) -> list[str]:
    return config.get("ratings", {}).get("preference", list(_DEFAULT_PREFERENCE))


def get_rating_map(config: dict) -> dict[str, dict[str, int | None]]:
    config_map = config.get("ratings", {}).get("map", {})
    merged: dict[str, dict[str, int | None]] = {}
    for scheme, defaults in _DEFAULT_MAP.items():
        merged[scheme] = {**defaults, **config_map.get(scheme, {})}
    for scheme, overrides in config_map.items():
        if scheme not in merged:
            merged[scheme] = dict(overrides)
    return merged
