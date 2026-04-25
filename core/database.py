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


def load_games() -> dict:
    if not GAMES_FILE.exists():
        return {}
    with open(GAMES_FILE, encoding="utf-8") as f:
        return json.load(f)


def save_games(games: dict) -> None:
    _atomic_write(GAMES_FILE, games)
