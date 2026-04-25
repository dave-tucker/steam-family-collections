import json

from core.config import CHILDREN_DIR
from core.database import _atomic_write


def load_child(name: str) -> dict | None:
    path = CHILDREN_DIR / f"{name}.json"
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_child(child: dict) -> None:
    CHILDREN_DIR.mkdir(parents=True, exist_ok=True)
    _atomic_write(CHILDREN_DIR / f"{child['name']}.json", child)


def delete_child(name: str) -> None:
    path = CHILDREN_DIR / f"{name}.json"
    if path.exists():
        path.unlink()


def list_children() -> list[dict]:
    CHILDREN_DIR.mkdir(parents=True, exist_ok=True)
    result = []
    for path in sorted(CHILDREN_DIR.glob("*.json")):
        with open(path, encoding="utf-8") as f:
            result.append(json.load(f))
    return result


def compute_library(child: dict, games: dict) -> list[int]:
    max_age = child["max_age"]
    return sorted(
        int(appid)
        for appid, game in games.items()
        if game.get("pegi_rating") is not None
        and game.get("pegi_flag") is None
        and game["pegi_rating"] <= max_age
    )


def sync_child(child: dict, games: dict) -> tuple[int, int]:
    old = set(child.get("library", []))
    new = set(compute_library(child, games))
    child["library"] = sorted(new)
    return len(new - old), len(old - new)
