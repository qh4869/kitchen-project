"""Local-disk FileStorage. Files written under root/, served via /static/."""

from pathlib import Path

from app.services.storage.adapter import FileStorage


class LocalFileStorage:
    """Writes files to a local directory.

    `key` is interpreted as a relative path under root. Caller is responsible
    for using safe keys (we generate them with uuid + date prefix).
    """

    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    async def save(self, data: bytes, key: str) -> str:
        path = self._safe_path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return key

    async def read(self, key: str) -> bytes:
        path = self._safe_path(key)
        if not path.exists():
            raise FileNotFoundError(key)
        return path.read_bytes()

    async def delete(self, key: str) -> None:
        path = self._safe_path(key)
        if path.exists():
            path.unlink()

    def get_url(self, key: str) -> str:
        return f"/static/{key}"

    def _safe_path(self, key: str) -> Path:
        # Resolve and ensure the result stays under root
        path = (self.root / key).resolve()
        root_resolved = self.root.resolve()
        if not str(path).startswith(str(root_resolved)):
            raise ValueError(f"key escapes storage root: {key!r}")
        return path


# FileStorage is a runtime_checkable Protocol; LocalFileStorage satisfies it structurally.
_externally_typed: FileStorage = LocalFileStorage(root="/tmp")  # type: ignore[assignment]
