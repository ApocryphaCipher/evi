"""Content-addressed storage. Originals are stored once and never changed.

Every blob is zstd-compressed and named by the SHA-256 of its original
bytes, so the name proves the content. Large memory dumps can instead be
stored as 4 KB pages: consecutive dumps share almost all their pages, so
each new dump costs only the pages that changed, and the exact original
can still be rebuilt byte for byte.
"""

import hashlib
from compression import zstd
from pathlib import Path

PAGE_SIZE = 4096
DIGEST_SIZE = 32


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class BlobStore:
    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def path(self, sha: str) -> Path:
        return self.root / sha[:2] / f"{sha}.zst"

    def has(self, sha: str) -> bool:
        return self.path(sha).exists()

    def put(self, data: bytes) -> str:
        sha = sha256(data)
        path = self.path(sha)
        if not path.exists():
            path.parent.mkdir(exist_ok=True)
            tmp = path.with_suffix(".tmp")
            tmp.write_bytes(zstd.compress(data, level=10))
            tmp.rename(path)
        return sha

    def get(self, sha: str) -> bytes:
        data = zstd.decompress(self.path(sha).read_bytes())
        if sha256(data) != sha:
            raise ValueError(f"blob {sha} is corrupt")
        return data

    def put_paged(self, data: bytes) -> tuple[str, str]:
        """Store data as pages. Returns (sha of the whole, sha of the manifest)."""
        digests = bytearray()
        for start in range(0, len(data), PAGE_SIZE):
            digests += bytes.fromhex(self.put(data[start : start + PAGE_SIZE]))
        manifest = len(data).to_bytes(8, "little") + bytes(digests)
        return sha256(data), self.put(manifest)

    def get_paged(self, manifest_sha: str) -> bytes:
        manifest = self.get(manifest_sha)
        size = int.from_bytes(manifest[:8], "little")
        digests = manifest[8:]
        data = b"".join(
            self.get(digests[i : i + DIGEST_SIZE].hex())
            for i in range(0, len(digests), DIGEST_SIZE)
        )
        assert len(data) == size
        return data

    def all(self) -> list[str]:
        return sorted(p.stem for p in self.root.glob("*/*.zst"))
