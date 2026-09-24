"""A vault: a blob store plus a catalogue, in one directory.

Ingesting never changes an original. Archives are stored whole, and their
members are also catalogued as child items so their text can be searched.
"""

import fnmatch
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from evi import extract
from evi.blobs import BlobStore, sha256
from evi.catalog import Catalog

MAX_ARCHIVE_DEPTH = 2


@dataclass
class Provenance:
    collection: str
    source: str | None = None
    author: str | None = None
    license: str | None = None
    note: str | None = None


class Vault:
    def __init__(self, home: Path):
        self.home = home
        self.blobs = BlobStore(home / "blobs")
        self.catalog = Catalog(home / "catalog.sqlite")

    def add_path(self, root: Path, prov: Provenance, exclude: list[str]) -> list[tuple[int, str, bool]]:
        """Add a file or a directory tree. Returns (item id, path, was new)."""
        files = [root] if root.is_file() else sorted(p for p in root.rglob("*") if p.is_file())
        results = []
        for path in files:
            if path.name == ".DS_Store" or any(fnmatch.fnmatch(str(path), pat) for pat in exclude):
                continue
            file_time = datetime.fromtimestamp(path.stat().st_mtime, UTC).isoformat(timespec="seconds")
            results += self._add(path.read_bytes(), path.name, str(path), None, prov, file_time, depth=0)
        self.catalog.commit()
        return results

    def add_bytes(
        self, data: bytes, name: str, path: str, prov: Provenance,
        parent_id: int | None = None, file_time: str | None = None,
    ) -> int:
        """Add evidence that doesn't come from a file (e.g. captured over an
        API). `path` records where it came from; `parent_id` attaches it to
        another item, such as a screenshot to the dump taken with it."""
        item_id = self._add(data, name, path, parent_id, prov, file_time, depth=0)[0][0]
        self.catalog.commit()
        return item_id

    def _add(self, data, name, path, parent_id, prov, file_time, depth) -> list[tuple[int, str, bool]]:
        sha = sha256(data)
        existing = self.catalog.find_item(prov.collection, path, sha)
        if existing:
            return [(existing, path, False)]

        kind = extract.kind_of(name, len(data))
        if kind == "ramdump":
            _, manifest = self.blobs.put_paged(data)
            storage = "paged"
        else:
            self.blobs.put(data)
            manifest, storage = None, "blob"

        item_id = self.catalog.add_item(
            sha256=sha, size=len(data), kind=kind, storage=storage, manifest_sha256=manifest,
            name=name, path=path, parent_id=parent_id, collection=prov.collection,
            source=prov.source, author=prov.author, license=prov.license,
            file_time=file_time, note=prov.note,
        )
        results = [(item_id, path, True)]

        if kind not in ("ramdump", "image"):
            text = extract.text_of(name, data)
            if text:
                self.catalog.add_text(item_id, text)

        if kind == "archive" and depth < MAX_ARCHIVE_DEPTH:
            for member, member_data in extract.archive_members(data):
                results += self._add(
                    member_data, member.rsplit("/", 1)[-1], f"{path}!{member}",
                    item_id, prov, None, depth + 1,
                )
        return results

    def original(self, item_id: int) -> bytes:
        row = self.catalog.db.execute(
            "SELECT sha256, storage, manifest_sha256 FROM items WHERE id = ?", (item_id,)
        ).fetchone()
        if row is None:
            raise KeyError(f"no item {item_id}")
        if row["storage"] == "paged":
            return self.blobs.get_paged(row["manifest_sha256"])
        return self.blobs.get(row["sha256"])

    def verify(self) -> list[str]:
        """Re-read every item and check its hash. Returns the problems found."""
        problems = []
        for row in self.catalog.db.execute("SELECT id, sha256, path FROM items"):
            try:
                if sha256(self.original(row["id"])) != row["sha256"]:
                    problems.append(f"item {row['id']} ({row['path']}): hash mismatch")
            except Exception as e:
                problems.append(f"item {row['id']} ({row['path']}): {e}")
        return problems
