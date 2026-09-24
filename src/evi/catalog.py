"""The catalogue: what each piece of evidence is, where it came from, what
it says, and which claims it supports."""

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY,
    sha256 TEXT NOT NULL,
    size INTEGER NOT NULL,
    kind TEXT NOT NULL,          -- ramdump, archive, image, document, binary
    storage TEXT NOT NULL,       -- blob, or paged (ramdump pages)
    manifest_sha256 TEXT,        -- for paged items
    name TEXT NOT NULL,
    path TEXT NOT NULL,          -- original path, or member path inside the parent
    parent_id INTEGER REFERENCES items(id),
    collection TEXT NOT NULL,
    source TEXT,                 -- where it came from
    author TEXT,
    license TEXT,                -- what may be done with it
    publish TEXT NOT NULL DEFAULT 'cite',  -- embed, excerpt, cite, never (see report.py)
    file_time TEXT,              -- the file's own date
    added_at TEXT NOT NULL,
    note TEXT,
    UNIQUE (collection, path, sha256)
);
CREATE INDEX IF NOT EXISTS items_sha ON items(sha256);

CREATE VIRTUAL TABLE IF NOT EXISTS texts USING fts5(item_id UNINDEXED, text);

CREATE TABLE IF NOT EXISTS claims (
    id INTEGER PRIMARY KEY,
    statement TEXT NOT NULL,
    topic TEXT,                  -- groups claims into a report
    status TEXT NOT NULL CHECK (status IN ('checked', 'guess', 'refuted')),
    test TEXT,                   -- what would settle it (for guesses)
    reference TEXT,              -- where it's written up
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS claim_evidence (
    claim_id INTEGER NOT NULL REFERENCES claims(id),
    item_id INTEGER NOT NULL REFERENCES items(id),
    role TEXT NOT NULL CHECK (role IN ('supports', 'contradicts', 'context')),
    detail TEXT,                 -- e.g. the offset or the screen text relied on
    offset INTEGER,              -- bytes of the item the claim rests on, quoted in reports
    length INTEGER,
    PRIMARY KEY (claim_id, item_id, role)
);
"""


def now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


class Catalog:
    def __init__(self, path: Path):
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys = ON")
        self.db.executescript(SCHEMA)
        self._migrate()

    def _migrate(self) -> None:
        """Add columns introduced after a catalogue was created."""
        added = {
            "items": [("publish", "TEXT NOT NULL DEFAULT 'cite'")],
            "claims": [("topic", "TEXT")],
            "claim_evidence": [("offset", "INTEGER"), ("length", "INTEGER")],
        }
        for table, columns in added.items():
            have = {row["name"] for row in self.db.execute(f"PRAGMA table_info({table})")}
            for name, decl in columns:
                if name not in have:
                    self.db.execute(f"ALTER TABLE {table} ADD COLUMN {name} {decl}")
        self.db.commit()

    def find_item(self, collection: str, path: str, sha: str) -> int | None:
        row = self.db.execute(
            "SELECT id FROM items WHERE collection = ? AND path = ? AND sha256 = ?",
            (collection, path, sha),
        ).fetchone()
        return row["id"] if row else None

    def add_item(self, **fields) -> int:
        fields.setdefault("added_at", now())
        cols = ", ".join(fields)
        marks = ", ".join("?" * len(fields))
        cur = self.db.execute(f"INSERT INTO items ({cols}) VALUES ({marks})", tuple(fields.values()))
        return cur.lastrowid

    def add_text(self, item_id: int, text: str) -> None:
        self.db.execute("INSERT INTO texts (item_id, text) VALUES (?, ?)", (item_id, text))

    def search(self, query: str, limit: int = 20) -> list[sqlite3.Row]:
        return self.db.execute(
            "SELECT i.id, i.collection, i.path, snippet(texts, 1, '[', ']', ' … ', 12) AS hit"
            " FROM texts JOIN items i ON i.id = texts.item_id"
            " WHERE texts MATCH ? ORDER BY rank LIMIT ?",
            (query, limit),
        ).fetchall()

    def add_claim(
        self, statement: str, status: str, test: str | None, reference: str | None,
        topic: str | None = None,
    ) -> int:
        stamp = now()
        cur = self.db.execute(
            "INSERT INTO claims (statement, topic, status, test, reference, created_at, updated_at)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (statement, topic, status, test, reference, stamp, stamp),
        )
        return cur.lastrowid

    def link(
        self, claim_id: int, item_id: int, role: str, detail: str | None,
        offset: int | None = None, length: int | None = None,
    ) -> None:
        self.db.execute(
            "INSERT OR REPLACE INTO claim_evidence (claim_id, item_id, role, detail, offset, length)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (claim_id, item_id, role, detail, offset, length),
        )

    def set_publish(self, where: str, params: tuple, value: str) -> int:
        cur = self.db.execute(f"UPDATE items SET publish = ? WHERE {where}", (value, *params))
        return cur.rowcount

    def commit(self) -> None:
        self.db.commit()
