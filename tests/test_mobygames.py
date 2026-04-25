import pytest

from core.mobygames import _parse_pegi, candidate_summary, clean_title


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
        ({"rating_system_name": "PEGI", "rating_name": "PEGI 12"}, 12),
        ({"rating_system_name": "PEGI", "rating_name": "PEGI 3"}, 3),
        ({"rating_system_name": "PEGI", "rating_name": "PEGI 18"}, 18),
        # Values snap up to the next valid bracket
        ({"rating_system_name": "PEGI", "rating_name": "15"}, 16),
        ({"rating_system_name": "PEGI", "rating_name": "6"}, 7),
        # Non-PEGI systems ignored
        ({"rating_system_name": "ESRB", "rating_name": "T"}, None),
        ({"rating_system_name": "USK", "rating_name": "12"}, None),
        # Malformed entries
        ({"rating_system_name": "PEGI", "rating_name": "Adult"}, None),
        ({}, None),
    ],
)
def test_parse_pegi(rating, expected):
    assert _parse_pegi(rating) == expected


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
