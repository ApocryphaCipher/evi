# Evi docs

**Picking this up? Read [notes/2026-10-08-handoff.md](notes/2026-10-08-handoff.md) first.**
For what Evi is and how to run it, see the [README](../README.md).

Working docs for Evi (evidence), the evidence store and catalogue of
**ApocryphaCipher**: delving into the apocryphal to reconstruct long-lost,
undocumented code, namely 90s DOS games. It sits beside
[gama](https://github.com/ApocryphaCipher/gama) (game-state analytics) and the
[DOSBox fork](https://github.com/ApocryphaCipher/dosbox-staging/tree/webserver-write-guard)
(the instrumented machine). Not shipped; this is planning and reference scaffolding.

- [`reference/`](reference): what Evi does *now*, checked against the code
  - [vault-layout.md](reference/vault-layout.md): what is on disk, how a file is stored and found again, and what "verify" proves
- [`epics/`](epics): large bodies of work, one file each, status at the top
- [`stories/`](stories): units of work, indexed in [stories/README.md](stories/README.md)
- [`backlog.md`](backlog.md): unsorted ideas and known issues
- [`notes/`](notes): dated session notes; the newest handoff is the entry point

## Rules Evi keeps

- **Originals are never changed.** Each is stored once and named by a hash.
  `evi verify` re-hashes everything.
- **Every item has provenance** (collection, source, author, licence, the file's
  own date, when it was added).
- **Claims are `checked`, `guess` or `refuted`**, and a guess names the test that
  would settle it. Mark guesses as guesses everywhere, here too.
- **Code and data are separate.** This repo is the tool; evidence lives in a
  vault directory, which is private (other people's files, game data) and is
  never committed here.
- **Done means checked:** `uv run pytest` passes. A fix comes with a test that
  fails without it. Build synthetic fixtures in the test; never commit a real
  dump or a game file.
- **Docs are product surface.** When behaviour changes, change the page that
  describes it in the same change.

Requires Python 3.14 or later (`requires-python = ">=3.14"`; `blobs.py` uses
`compression.zstd`).
