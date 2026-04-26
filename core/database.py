import json
import os
import tempfile

from core.config import CHILDREN_DIR, DATA_DIR, GAMES_FILE


def ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CHILDREN_DIR.mkdir(parents=True, exist_ok=True)


def _atomic_write(path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        dir=path.parent,
        delete=False,
        suffix=".tmp",
        encoding="utf-8",
    ) as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        tmp = f.name
    os.replace(tmp, path)


def _migrate_game(game: dict) -> None:
    """Migrate pre-ratings-refactor fields to the new schema (in-place)."""
    if "pegi_rating" not in game:
        return
    pegi_rating = game.pop("pegi_rating")
    pegi_source = game.pop("pegi_source", None)
    game.setdefault("ratings", {"pegi": str(pegi_rating)} if pegi_rating is not None else {})
    game.setdefault("age_rating", pegi_rating)
    if pegi_source == "manual":
        game.setdefault("rating_scheme", "manual")
    elif pegi_rating is not None:
        game.setdefault("rating_scheme", "pegi")
    else:
        game.setdefault("rating_scheme", None)


def load_games() -> dict:
    if not GAMES_FILE.exists():
        return {}
    with open(GAMES_FILE, encoding="utf-8") as f:
        games = json.load(f)
    for game in games.values():
        _migrate_game(game)
    return games


def save_games(games: dict) -> None:
    _atomic_write(GAMES_FILE, games)
