import json
from pathlib import Path
from unittest.mock import patch

from core import collection


def _write_cloud_file(path: Path, collections: dict) -> None:
    """Write a cloud file in the real [key, entry] list format."""
    entries = []
    for cid, col in collections.items():
        entries.append([
            f"user-collections.{cid}",
            {
                "key": f"user-collections.{cid}",
                "timestamp": col.get("timestamp", 0),
                "value": json.dumps(col),
                "version": "1",
            },
        ])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(entries))


def _read_collections(path: Path) -> dict:
    """Return a dict of collection_id -> collection_data from the real format."""
    entries = json.loads(path.read_text())
    result = {}
    for entry in entries:
        if not isinstance(entry, list) or len(entry) != 2:
            continue
        key, obj = entry
        if not isinstance(key, str) or not key.startswith("user-collections."):
            continue
        if obj.get("is_deleted") or not obj.get("value"):
            continue
        value = json.loads(obj["value"])
        result[value["id"]] = value
    return result


def test_push_creates_new_collection(tmp_path):
    path = tmp_path / "cloud-storage-namespace-1.json"
    with patch.object(collection, "get_collection_path", return_value=path):
        cid = collection.push_collection("12345", "Alice", [10, 20, 30])

    cols = _read_collections(path)
    assert cid in cols
    assert cols[cid]["name"] == "Alice"
    assert cols[cid]["added"] == [10, 20, 30]
    assert cols[cid]["removed"] == []


def test_push_updates_existing_collection(tmp_path):
    path = tmp_path / "cloud-storage-namespace-1.json"
    existing = {
        "abc-123": {"id": "abc-123", "name": "Alice", "added": [10], "removed": [], "timestamp": 0}
    }
    _write_cloud_file(path, existing)
    with patch.object(collection, "get_collection_path", return_value=path):
        cid = collection.push_collection("12345", "Alice", [10, 20])

    assert cid == "abc-123"
    cols = _read_collections(path)
    assert cols["abc-123"]["added"] == [10, 20]


def test_push_preserves_other_entries(tmp_path):
    path = tmp_path / "cloud-storage-namespace-1.json"
    existing = {
        "favorite": {"id": "favorite", "name": "Favorites", "added": [730], "removed": []},
    }
    _write_cloud_file(path, existing)
    with patch.object(collection, "get_collection_path", return_value=path):
        collection.push_collection("12345", "Alice", [10])

    cols = _read_collections(path)
    assert "favorite" in cols
    assert "Alice" in [c["name"] for c in cols.values()]


def test_push_creates_backup(tmp_path):
    path = tmp_path / "cloud-storage-namespace-1.json"
    _write_cloud_file(path, {})
    with patch.object(collection, "get_collection_path", return_value=path):
        collection.push_collection("12345", "Bob", [1])

    assert path.with_suffix(".json.bak").exists()


def test_push_no_backup_when_file_absent(tmp_path):
    path = tmp_path / "cloud-storage-namespace-1.json"
    with patch.object(collection, "get_collection_path", return_value=path):
        collection.push_collection("12345", "Bob", [1])

    assert not path.with_suffix(".json.bak").exists()


def test_push_appids_sorted(tmp_path):
    path = tmp_path / "cloud-storage-namespace-1.json"
    with patch.object(collection, "get_collection_path", return_value=path):
        cid = collection.push_collection("12345", "Alice", [30, 10, 20])

    cols = _read_collections(path)
    assert cols[cid]["added"] == [10, 20, 30]


def test_push_increments_version(tmp_path):
    path = tmp_path / "cloud-storage-namespace-1.json"
    existing = {
        "favorite": {"id": "favorite", "name": "Favorites", "added": [], "removed": []},
    }
    _write_cloud_file(path, existing)
    with patch.object(collection, "get_collection_path", return_value=path):
        collection.push_collection("12345", "Alice", [1])

    entries = json.loads(path.read_text())
    versions = [int(e[1]["version"]) for e in entries if isinstance(e, list)]
    assert max(versions) == 2  # existing was version 1, new entry is 2
