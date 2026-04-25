import json
from pathlib import Path
from unittest.mock import patch

from core import collection


def _write_cloud_file(path: Path, collections: dict) -> None:
    inner = {"UserCollections": {"collections": collections}}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"version": 2, "Data": json.dumps(inner)}))


def _read_collections(path: Path) -> dict:
    data = json.loads(path.read_text())
    inner = json.loads(data["Data"])
    return inner["UserCollections"]["collections"]


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
