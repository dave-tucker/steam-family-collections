import pytest

from core.ratings import apply_map, get_rating_map, normalize_scheme, select_rating

_MAP = {
    "esrb": {"EC": 3, "E": 3, "E10+": 7, "T": 12, "M": 16, "AO": 18, "RP": None},
    "bbfc": {"U": 0, "PG": 5, "12A": 12, "12": 12, "15": 15, "18": 18, "R18": 18},
}


@pytest.mark.parametrize(
    "system_name, expected",
    [
        ("PEGI Rating", "pegi"),
        ("ESRB Rating", "esrb"),
        ("USK Rating", "usk"),
        ("PEGI/BBFC Rating", "bbfc"),  # BBFC matched before PEGI in alias order? No — BBFC first
        ("ClassInd Rating", "classind"),
        ("SomeUnknownBoard", None),
    ],
)
def test_normalize_scheme(system_name, expected):
    assert normalize_scheme(system_name) == expected


@pytest.mark.parametrize(
    "scheme, raw, expected",
    [
        # Exact map match
        ("esrb", "T", 12),
        ("esrb", "M", 16),
        ("esrb", "E10+", 7),
        ("esrb", "RP", None),
        # First-token match ("T - Teen 13+" → "T")
        ("esrb", "T - Teen 13+", 12),
        ("esrb", "M - Mature 17+", 16),
        # BBFC
        ("bbfc", "PG", 5),
        ("bbfc", "12A", 12),
        ("bbfc", "U", 0),
        # Digit extraction fallback (no map entry)
        ("pegi", "PEGI 12", 12),
        ("pegi", "PEGI 3", 3),
        ("usk", "USK 0", 0),
        ("usk", "12", 12),
        # Unknown scheme with digits
        ("grb", "15", 15),
        # Nothing resolvable
        ("esrb", "RP", None),
        ("unknown", "Adults Only", None),
    ],
)
def test_apply_map(scheme, raw, expected):
    assert apply_map(scheme, raw, _MAP) == expected


@pytest.mark.parametrize(
    "ratings, preference, expected_scheme, expected_age",
    [
        # Picks first preference that resolves
        ({"pegi": "12", "esrb": "T"}, ["bbfc", "pegi", "esrb"], "pegi", 12),
        ({"bbfc": "15", "pegi": "16"}, ["bbfc", "pegi"], "bbfc", 15),
        # Falls through to second preference when first absent
        ({"pegi": "12"}, ["bbfc", "pegi"], "pegi", 12),
        # Falls back to average when nothing in preference
        ({"pegi": "12", "usk": "12"}, ["bbfc", "esrb"], "average", 12),
        ({"pegi": "12", "esrb": "M"}, ["bbfc"], "average", 14),  # (12+16)//2 = 14
        # Empty ratings → None
        ({}, ["pegi", "esrb"], None, None),
        # All unresolvable (RP has no digits, unknown scheme no map)
        ({"esrb": "RP"}, ["pegi"], None, None),
    ],
)
def test_select_rating(ratings, preference, expected_scheme, expected_age):
    result = select_rating(ratings, preference, _MAP)
    if expected_scheme is None:
        assert result is None
    else:
        assert result is not None
        scheme, age = result
        assert scheme == expected_scheme
        assert age == expected_age


def test_get_rating_map_merges_defaults():
    config = {"ratings": {"map": {"esrb": {"X": 99}}}}
    merged = get_rating_map(config)
    assert merged["esrb"]["X"] == 99
    assert merged["esrb"]["T"] == 12  # default preserved
    assert "bbfc" in merged  # default scheme present


def test_get_rating_map_no_config():
    merged = get_rating_map({})
    assert merged["esrb"]["T"] == 12
    assert merged["bbfc"]["PG"] == 5
