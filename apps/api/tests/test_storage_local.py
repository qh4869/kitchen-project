from pathlib import Path

import pytest

from app.services.storage.local import LocalFileStorage


async def test_save_writes_file_and_returns_key(tmp_path: Path):
    storage = LocalFileStorage(root=tmp_path)
    key = await storage.save(b"hello", "2026/06/17/abc.jpg")
    assert key == "2026/06/17/abc.jpg"
    assert (tmp_path / "2026/06/17/abc.jpg").read_bytes() == b"hello"


async def test_save_creates_nested_dirs(tmp_path: Path):
    storage = LocalFileStorage(root=tmp_path)
    await storage.save(b"x", "2026/06/17/deep/path/file.jpg")
    assert (tmp_path / "2026/06/17/deep/path/file.jpg").exists()


async def test_read_returns_bytes(tmp_path: Path):
    storage = LocalFileStorage(root=tmp_path)
    await storage.save(b"abc", "f.jpg")
    assert await storage.read("f.jpg") == b"abc"


async def test_read_missing_raises_not_found(tmp_path: Path):
    storage = LocalFileStorage(root=tmp_path)
    with pytest.raises(FileNotFoundError):
        await storage.read("missing.jpg")


async def test_delete_removes_file(tmp_path: Path):
    storage = LocalFileStorage(root=tmp_path)
    await storage.save(b"x", "f.jpg")
    await storage.delete("f.jpg")
    assert not (tmp_path / "f.jpg").exists()


def test_get_url_returns_static_path(tmp_path: Path):
    storage = LocalFileStorage(root=tmp_path)
    assert storage.get_url("2026/06/17/abc.jpg") == "/static/2026/06/17/abc.jpg"
