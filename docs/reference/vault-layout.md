# The vault: layout and storage

A **vault** is one directory per subject (for example `~/repo/mom-evi-vault` for
Master of Magic), chosen with `EVI_HOME` or `--home`. It holds other people's
files and game data, so it is private and is not committed anywhere.

Source: [`blobs.py`](../../src/evi/blobs.py), [`vault.py`](../../src/evi/vault.py),
[`catalog.py`](../../src/evi/catalog.py), [`extract.py`](../../src/evi/extract.py).

## On disk

```text
<vault>/
  blobs/<aa>/<sha256>.zst   every stored blob, in a folder named by its first two hex digits
  catalog.sqlite            what each item is, where it came from, what it says, which claims it backs
  derived/                  other tools' databases (gama puts gama.sqlite here); Evi never reads them
  reports/                  where `evi report -o reports/<topic>` is conventionally pointed (the folder is your choice)
  README.md                 the vault's own notes
```

Only `blobs/` and `catalog.sqlite` are Evi's. `derived/` can be deleted and
rebuilt by the tool that made it.

## Blobs

- A blob is **zstd-compressed (level 10)** and its file name is the **SHA-256
  of its original bytes**, so the name proves the content. `get()` re-hashes
  after decompressing and raises "blob ... is corrupt" on a mismatch.
- Writes go to a `.tmp` file that is renamed into place, so a crash can't leave a
  half-written blob under a real name.
- Putting bytes that are already stored does nothing.

## Items

An **item** is one catalogued file. Its `kind` decides how it is stored:

| `kind` | How decided | `storage` | Text indexed? |
| --- | --- | --- | --- |
| `ramdump` | name ends `.bin` **and** size is exactly 16 MiB (16,777,216 bytes) | `paged` | no |
| `archive` | `.zip` | `blob` | no, but its members are (below) |
| `image` | `.png .jpg .jpeg .gif .webp .bmp .pcx` | `blob` | no |
| `document` | text, HTML, RTF or PDF suffixes (list in `extract.py`) | `blob` | yes |
| `binary` | anything else | `blob` | yes, if more than 90% of the first 4 KB is printable |

A 16 MiB file that isn't named `.bin` is a `binary`, stored whole; a `.bin` of any
other size is too. So "paged" depends on both name and size.

### Paged storage (RAM dumps)

The dump is cut into 4,096-byte pages. Each page is a blob (named by its own
hash). A **manifest** blob lists them: an 8-byte little-endian total size, then
the 32-byte digest of each page in order. The item records:

- `sha256`: the hash of the **whole dump**, which is what identifies it;
- `manifest_sha256`: the manifest's blob name.

**There is no blob named by the whole dump's hash.** The "name proves content"
rule holds for each page and the manifest; for the dump as a whole,
`evi verify` is what proves it, by rebuilding it and re-hashing. Consecutive
dumps share most pages, so each new one costs only its changed pages plus a
manifest (a test in `tests/test_evi.py` checks exactly that).

`evi get` rebuilds the dump byte for byte.

### Archives

A `.zip` is stored whole. Each file inside is also catalogued as a **child item**
with `path` = `archive.zip!member/path` and `parent_id` pointing at the archive,
so its text is searchable. Archives inside archives are unpacked to a depth of 2
(`MAX_ARCHIVE_DEPTH`). A zip that can't be read (bad, encrypted, or an unsupported
method) is stored but has no members.

### Provenance and duplicates

Every item has a collection, `source`, `author`, `license`, `note`, the file's own
modification time (`file_time`) and when it was added (`added_at`).

An item is unique by **(collection, path, hash)**. The same bytes at the same path
in the same collection is one item, and adding it again is counted as "already
catalogued" (`evi add -v` marks it `known`). The
same bytes found at another path, or in another collection, is a **new item that
shares the stored blob**. `.DS_Store` files are skipped.

`add_bytes()` is for evidence that isn't a file, such as a capture over an API:
`path` records where it came from, and `parent_id` attaches it to another item (a
screenshot to the dump taken with it). gama uses this.

## Search

`texts` is an SQLite FTS5 table of extracted text. DOS-era text is decoded as
Latin-1, which never fails and keeps ASCII; runs of spaces are collapsed.
Extraction failures are swallowed, so an unreadable PDF is simply not searchable.

## Claims and evidence

| Table | Notes |
| --- | --- |
| `claims` | `status` must be `checked`, `guess` or `refuted` (an SQL check). `test` is what would settle a guess. `topic` groups claims into a report |
| `claim_evidence` | primary key (claim, item, role). `role` is `supports`, `contradicts` or `context`. `offset`/`length` mark the bytes relied on |

**Linking the same claim, item and role again replaces the earlier row** (the
`detail`, `offset` and `length` are overwritten), because the insert is
`INSERT OR REPLACE`. To keep two details for one item, use two roles or two claims.

`items.publish` (`embed`, `excerpt`, `cite`, `never`; default `cite`) says what
`evi report` may do with an item. See the README's table.

## What `evi verify` proves

It re-reads every item through `original()` and compares the hash to the
catalogue. That catches a corrupt or missing blob, and a paged item whose pages
no longer rebuild to the recorded hash. It does **not** prove that the
catalogue's provenance is true; that is only as good as what was typed at `add`.

## Schema changes

`catalog.py` creates tables if missing and `_migrate()` adds columns introduced
later (`publish`, `topic`, `offset`, `length`) to an older catalogue. It does not
drop or rename anything.
