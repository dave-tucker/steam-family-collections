import pytest

from core.mobygames import _parse_rating, candidate_summary, clean_title


@pytest.mark.parametrize(
    "raw, expected",
    [
        # Edition keyword strips the keyword + everything after, but leaves preceding words
        ("The Witcher 3™: Wild Hunt - Game of the Year Edition", "The Witcher 3 Wild Hunt"),
        ("BioShock® Infinite: Complete Edition", "BioShock Infinite"),
        ("DOOM (2016)", "DOOM"),
        # Non-edition subtitles after colon are kept
        (
            "Sid Meier's Civilization® VI: Rise and Fall",
            "Sid Meier's Civilization VI Rise and Fall",
        ),
        # Unknown suffixes after dash are not stripped
        ("Sonic Mania - Plus", "Sonic Mania - Plus"),
        ("Metro Exodus: Enhanced Edition", "Metro Exodus"),
        ("Hades", "Hades"),
        ("Grand Theft Auto V", "Grand Theft Auto V"),
        # "The Final Cut" is not in the edition keyword list (Director's Cut is)
        ("Disco Elysium - The Final Cut", "Disco Elysium - The Final Cut"),
        # Bare "Edition" without a qualifying keyword is not stripped
        ("NieR: Automata - BECOME AS GODS Edition", "NieR Automata - BECOME AS GODS Edition"),
        ("Elden Ring - Deluxe Edition", "Elden Ring"),
        ("What Remains of Edith Finch", "What Remains of Edith Finch"),
        ("Death's Door", "Death's Door"),
        ("Persona 4 Golden", "Persona 4 Golden"),
    ],
)
def test_clean_title(raw, expected):
    assert clean_title(raw) == expected


@pytest.mark.parametrize(
    "rating, expected",
    [
        # PEGI ratings return (scheme, raw_value)
        ({"rating_system_name": "PEGI Rating", "rating_name": "PEGI 12"}, ("pegi", "PEGI 12")),
        ({"rating_system_name": "PEGI Rating", "rating_name": "PEGI 3"}, ("pegi", "PEGI 3")),
        ({"rating_system_name": "PEGI Rating", "rating_name": "18"}, ("pegi", "18")),
        # ESRB
        ({"rating_system_name": "ESRB Rating", "rating_name": "T - Teen"}, ("esrb", "T - Teen")),
        (
            {"rating_system_name": "ESRB Rating", "rating_name": "M - Mature 17+"},
            ("esrb", "M - Mature 17+"),
        ),
        # USK
        ({"rating_system_name": "USK Rating", "rating_name": "12"}, ("usk", "12")),
        # BBFC (via PEGI/BBFC combined system name)
        ({"rating_system_name": "PEGI/BBFC Rating", "rating_name": "12"}, ("bbfc", "12")),
        # Unknown system
        ({"rating_system_name": "ACB Rating", "rating_name": "MA15+"}, ("acb", "MA15+")),
        # Completely unknown system → None
        ({"rating_system_name": "SomeUnknownBoard", "rating_name": "7"}, None),
        # Missing rating_name → None
        ({"rating_system_name": "PEGI Rating", "rating_name": ""}, None),
        # Empty dict → None
        ({}, None),
    ],
)
def test_parse_rating(rating, expected):
    assert _parse_rating(rating) == expected


def test_candidate_summary_full():
    game = {
        "title": "Portal 2",
        "first_release_date": "2011-04-19",
        "platforms": [
            {"platform_name": "PC"},
            {"platform_name": "PS3"},
            {"platform_name": "Xbox 360"},
        ],
    }
    result = candidate_summary(game)
    assert result == "Portal 2 (2011) — PC, PS3, Xbox 360"


def test_candidate_summary_missing_fields():
    result = candidate_summary({})
    assert "Unknown" in result
    assert "?" in result
