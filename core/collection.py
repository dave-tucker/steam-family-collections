# Steam cloud-storage-namespace-1.json schema (real format)
#
# Top-level: JSON array of [key, entry] pairs.
#
# Each entry object has:
#   "key"        (str):  same as the array key
#   "timestamp"  (int):  Unix epoch of last modification
#   "value"      (str):  JSON-encoded payload (absent on deleted entries)
#   "version"    (str):  monotonically increasing integer as a string
#   "is_deleted" (bool): present and true on tombstone entries
#
# User collections have keys of the form "user-collections.<id>".
# The parsed "value" payload contains:
#   "id"       (str):   collection ID (matches suffix of key)
#   "name"     (str):   human-readable display name
#   "added"    (int[]): AppIDs included in the collection
#   "removed"  (int[]): AppIDs explicitly excluded
#
# File location (native install):
#   ~/.local/share/Steam/userdata/<user_id>/config/cloudstorage/cloud-storage-namespace-1.json
# Flatpak install:
#   ~/.var/app/com.valvesoftware.Steam/data/Steam/userdata/<user_id>/config/cloudstorage/...

import base64
import json
import os
import shutil
import tempfile
import time
from pathlib import Path

_COLLECTION_KEY_PREFIX = "user-collections."


def _default_steam_dir() -> Path:
    native = Path.home() / ".local/share/Steam"
    flatpak = Path.home() / ".var/app/com.valvesoftware.Steam/data/Steam"
    return native if native.exists() else flatpak


def get_collection_path(user_id: str, steam_dir: Path | None = None) -> Path:
    base = steam_dir or _default_steam_dir()
    return base / "userdata" / str(user_id) / "config/cloudstorage/cloud-storage-namespace-1.json"


def _load(path: Path) -> list:
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _save(path: Path, entries: list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        dir=path.parent,
        delete=False,
        suffix=".tmp",
        encoding="utf-8",
    ) as f:
        json.dump(entries, f)
        tmp = f.name
    os.replace(tmp, path)


def _random_id() -> str:
    return base64.b64encode(os.urandom(9)).decode()


def push_collection(
    user_id: str,
    collection_name: str,
    appids: list[int],
    steam_dir: Path | None = None,
) -> str:
    path = get_collection_path(user_id, steam_dir)

    if path.exists():
        shutil.copy2(path, path.with_suffix(".json.bak"))

    entries = _load(path)

    max_version = max(
        (
            int(e[1].get("version", 0))
            for e in entries
            if isinstance(e, list) and len(e) == 2 and isinstance(e[1], dict)
        ),
        default=0,
    )

    existing_idx: int | None = None
    existing_id: str | None = None
    for i, entry in enumerate(entries):
        if not isinstance(entry, list) or len(entry) != 2:
            continue
        key, obj = entry
        if not isinstance(key, str) or not key.startswith(_COLLECTION_KEY_PREFIX):
            continue
        if obj.get("is_deleted") or not obj.get("value"):
            continue
        try:
            value = json.loads(obj["value"])
            if value.get("name") == collection_name:
                existing_idx = i
                existing_id = value["id"]
                break
        except (json.JSONDecodeError, KeyError):
            continue

    cid = existing_id or f"uc-{_random_id()}"
    collection_data = {
        "id": cid,
        "name": collection_name,
        "added": sorted(int(a) for a in appids),
        "removed": [],
    }
    new_entry = [
        f"{_COLLECTION_KEY_PREFIX}{cid}",
        {
            "key": f"{_COLLECTION_KEY_PREFIX}{cid}",
            "timestamp": int(time.time()),
            "value": json.dumps(collection_data),
            "version": str(max_version + 1),
        },
    ]

    if existing_idx is not None:
        entries[existing_idx] = new_entry
    else:
        entries.append(new_entry)

    _save(path, entries)
    return cid
