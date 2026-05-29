import json
import tempfile
from pathlib import Path

from app.repositories.json_storage import JsonAtomicStore


def test_atomic_roundtrip():
    with tempfile.TemporaryDirectory() as tmp:
        store = JsonAtomicStore(Path(tmp))
        path = Path(tmp) / "sample.json"
        payload = {"schema_version": 1, "hello": "world"}
        store.write_json_atomic(path, payload)
        loaded = store.read_json(path)
        assert loaded == payload


def test_read_missing_returns_none():
    with tempfile.TemporaryDirectory() as tmp:
        store = JsonAtomicStore(Path(tmp))
        missing = Path(tmp) / "nope.json"
        assert store.read_json(missing) is None


def test_atomic_json_utf8():
    with tempfile.TemporaryDirectory() as tmp:
        store = JsonAtomicStore(Path(tmp))
        path = Path(tmp) / "cn.json"
        payload = {"实习": "日志"}
        store.write_json_atomic(path, payload)
        assert json.loads(path.read_text(encoding="utf-8")) == payload
