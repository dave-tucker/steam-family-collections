import json
from unittest.mock import patch

import core.config as config
from core import database


def test_save_and_load_games(tmp_path):
    games = {
        "1234": {
            "name": "Portal",
            "age_rating": 7,
            "rating_scheme": "pegi",
            "ratings": {"pegi": "7"},
        }
    }
    games_file = tmp_path / "games.json"
    with patch.object(config, "GAMES_FILE", games_file):
        database.save_games(games)
        loaded = database.load_games()
    assert loaded == games


def test_load_games_migrates_pegi_rating(tmp_path):
    old_games = {"1234": {"name": "Portal", "pegi_rating": 7, "pegi_source": "steam"}}
    games_file = tmp_path / "games.json"
    games_file.write_text(json.dumps(old_games))
    with patch.object(config, "GAMES_FILE", games_file):
        loaded = database.load_games()
    assert loaded["1234"]["age_rating"] == 7
    assert loaded["1234"]["rating_scheme"] == "pegi"
    assert loaded["1234"]["ratings"] == {"pegi": "7"}
    assert "pegi_rating" not in loaded["1234"]
    assert "pegi_source" not in loaded["1234"]


def test_load_games_migrates_manual_source(tmp_path):
    old_games = {"1": {"name": "X", "pegi_rating": 12, "pegi_source": "manual"}}
    games_file = tmp_path / "games.json"
    games_file.write_text(json.dumps(old_games))
    with patch.object(config, "GAMES_FILE", games_file):
        loaded = database.load_games()
    assert loaded["1"]["rating_scheme"] == "manual"


def test_load_games_missing_file(tmp_path):
    with patch.object(config, "GAMES_FILE", tmp_path / "missing.json"):
        assert database.load_games() == {}


def test_save_games_is_atomic(tmp_path):
    games_file = tmp_path / "games.json"
    games = {"99": {"name": "Test", "pegi_rating": 3}}
    with patch.object(config, "GAMES_FILE", games_file):
        database.save_games(games)
    assert games_file.exists()
    # No leftover tmp files
    assert list(tmp_path.glob("*.tmp")) == []


def test_save_games_valid_json(tmp_path):
    games_file = tmp_path / "games.json"
    games = {"1": {"name": "A"}, "2": {"name": "B"}}
    with patch.object(config, "GAMES_FILE", games_file):
        database.save_games(games)
    content = json.loads(games_file.read_text())
    assert content == games
