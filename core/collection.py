# Steam cloud-storage-namespace-1.json schema
#
# Top-level object:
#   "version"  (int): format version, observed value 2
#   "Data"     (str): JSON-encoded string containing all collection data
#
# After parsing the "Data" string the inner object contains:
#   "UserCollections":
#     "collections": dict keyed by UUID string, each entry:
#       "id"        (str):        UUID of this collection
#       "name"      (str):        human-readable display name
#       "added"     (int[]):      AppIDs included in the collection
#       "removed"   (int[]):      AppIDs explicitly removed
#       "timestamp" (int):        Unix epoch of last modification
#
# Note: some Steam versions store "Data" as a parsed object rather than
# a JSON-encoded string — both forms are handled below.
#
# File location:
#   ~/.local/share/Steam/userdata/<user_id>/config/cloudstorage/cloud-storage-namespace-1.json

import json
import os
import shutil
import tempfile
import time
import uuid
from pathlib import Path


def get_collection_path(user_id: str) -> Path:
    return (
        Path.home()
        / ".local/share/Steam/userdata"
        / str(user_id)
        / "config/cloudstorage/cloud-storage-namespace-1.json"
    )


def _load(path: Path) -> dict:
    if not path.exists():
        return {
            "version": 2,
            "Data": json.dumps({"UserCollections": {"collections": {}}}),
        }
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _save(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        dir=path.parent,
        delete=False,
        suffix=".tmp",
        encoding="utf-8",
    ) as f:
        json.dump(data, f)
        tmp = f.name
    os.replace(tmp, path)


def push_collection(user_id: str, collection_name: str, appids: list[int]) -> str:
    path = get_collection_path(user_id)

    if path.exists():
        shutil.copy2(path, path.with_suffix(".json.bak"))

    file_data = _load(path)

    raw = file_data.get("Data", "{}")
    inner = json.loads(raw) if isinstance(raw, str) else raw

    collections = (
        inner.setdefault("UserCollections", {}).setdefault("collections", {})
    )

    cid = next(
        (k for k, v in collections.items() if v.get("name") == collection_name),
        str(uuid.uuid4()),
    )
    collections[cid] = {
        "id": cid,
        "name": collection_name,
        "added": sorted(int(a) for a in appids),
        "removed": [],
        "timestamp": int(time.time()),
    }

    file_data["Data"] = json.dumps(inner) if isinstance(raw, str) else inner
    _save(path, file_data)
    return cid
