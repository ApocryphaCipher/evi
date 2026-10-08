# Backlog

Unsorted, not yet promoted to a story. Each item says how it was found.

- **`evi link` silently replaces.** Linking the same claim, item and role twice
  overwrites `detail`, `offset` and `length` (`INSERT OR REPLACE`). It's
  documented in [reference/vault-layout.md](reference/vault-layout.md), but
  the command prints nothing about it. Either say "updated" or keep both.
  *Found 2026-10-08 reading `catalog.py`.*
- **A `.bin` that is not exactly 16 MiB is stored whole, not paged.** Anyone
  dumping a different memory size (DOSBox's `memsize`) loses the page sharing
  without being told. The test is `RAM_DUMP_SIZE` in `extract.py`. Probably
  right to widen it (any `.bin` that is a multiple of 4 KB and over some size),
  but it changes what existing items would look like on a re-add, so decide first.
- **Text extraction failures are silent.** `text_of()` returns `None` on any
  error, so a broken PDF just isn't searchable. A count of "N items with no text"
  in `evi stats` would show how much is missing.
- **The CLI has no tests.** The 5 tests call the library: paged storage, adding
  archives with their text, claims and links, `add_bytes`, and one end-to-end
  report test (publish policy, the 64-byte excerpt cap, figures, and that the
  Markdown, HTML and MediaWiki files are written). Nothing runs `cli.py` (195
  lines): argument handling, `claims`, `stats`, `verify`, and the messages
  printed. *Counted 2026-10-08.*
- **No way to remove an item.** By design (originals are never changed), but
  there is no documented way to correct a wrong `collection` or `source`
  either, short of editing SQLite by hand. A `evi amend` that records the change
  would keep the provenance rule honest.
