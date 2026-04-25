import json
from unittest.mock import patch

from core import database


def test_save_and_load_games(tmp_path):
    games = {"1234": {"name": "Portal", "pegi_rating": 7}}
    games_file = tmp_path / "games.json"
    with patch.object(database, "GAMES_FILE", games_file):
        database.save_games(games)
        loaded = database.load_games()
    assert loaded == games


def test_load_games_missing_file(tmp_path):
    with patch.object(database, "GAMES_FILE", tmp_path / "missing.json"):
        assert database.load_games() == {}


def test_save_games_is_atomic(tmp_path):
    games_file = tmp_path / "games.json"
    games = {"99": {"name": "Test", "pegi_rating": 3}}
    with patch.object(database, "GAMES_FILE", games_file):
        database.save_games(games)
    assert games_file.exists()
    # No leftover tmp files
    assert list(tmp_path.glob("*.tmp")) == []


def test_save_games_valid_json(tmp_path):
    games_file = tmp_path / "games.json"
    games = {"1": {"name": "A"}, "2": {"name": "B"}}
    with patch.object(database, "GAMES_FILE", games_file):
        database.save_games(games)
    content = json.loads(games_file.read_text())
    assert content == games
