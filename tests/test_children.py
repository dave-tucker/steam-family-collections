from core.children import compute_library, sync_child

GAMES = {
    "10": {"name": "Game A", "pegi_rating": 3},
    "20": {"name": "Game B", "pegi_rating": 12},
    "30": {"name": "Game C", "pegi_rating": 16},
    "40": {"name": "Game D", "pegi_rating": 18},
    "50": {"name": "Game E", "pegi_rating": None},  # unrated
    "60": {"name": "Game F", "pegi_rating": 7, "pegi_flag": "violence"},  # flagged
}


def test_compute_library_age_7():
    result = compute_library({"max_age": 7}, GAMES)
    assert result == [10]


def test_compute_library_age_12():
    result = compute_library({"max_age": 12}, GAMES)
    assert result == [10, 20]


def test_compute_library_age_18():
    result = compute_library({"max_age": 18}, GAMES)
    assert result == [10, 20, 30, 40]


def test_compute_library_excludes_unrated():
    result = compute_library({"max_age": 18}, GAMES)
    assert 50 not in result


def test_compute_library_excludes_flagged():
    result = compute_library({"max_age": 18}, GAMES)
    assert 60 not in result


def test_sync_child_adds_new_games():
    child = {"max_age": 12, "library": [10]}
    added, removed = sync_child(child, GAMES)
    assert added == 1
    assert removed == 0
    assert child["library"] == [10, 20]


def test_sync_child_removes_stale_games():
    child = {"max_age": 3, "library": [10, 20]}
    added, removed = sync_child(child, GAMES)
    assert added == 0
    assert removed == 1
    assert child["library"] == [10]


def test_sync_child_no_change():
    child = {"max_age": 3, "library": [10]}
    added, removed = sync_child(child, GAMES)
    assert added == 0
    assert removed == 0
    assert child["library"] == [10]
