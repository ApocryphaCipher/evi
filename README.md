# Evi: evidence

An evidence store and catalogue for software forensics, part of
**ApocryphaCipher**: delving into the apocryphal to reconstruct long-lost,
undocumented code, namely 90s DOS games.

Evi keeps originals, says where each came from, makes their text
searchable, and links **claims** to the evidence for and against them.
It sits beside [gama](../gama) (game-state analytics), the DOSBox Staging
fork (the instrumented machine) and Mirror (the Master of Magic viewer).

## Rules

- **Originals are never changed.** Each file is stored once,
  zstd-compressed and named by its SHA-256, so the name proves the
  content. `evi verify` re-hashes everything.
- **Every item has provenance:** collection, source, author, licence, the
  file's own date, and when it was added. The same file found in two
  places is two items sharing one stored blob.
- **Claims are checked, guesses or refuted**, and a guess names the test
  that would settle it.
- **Code and data are separate.** This repo is the tool. The evidence
  lives in a vault directory, one per subject (e.g. `~/repo/mom-evi-vault`
  for Master of Magic), chosen with `EVI_HOME` or `--home`. Vaults are
  private: they hold other people's files and game data.

## Storage

- Ordinary files are single blobs.
- **16 MB RAM dumps are stored as 4 KB pages.** Consecutive dumps share
  almost every page (a median of 93 of 4,096 changed between Master of
  Magic checkpoints), so each new dump costs only its changed pages, and
  `evi get` still rebuilds it byte for byte.
- Zip archives are stored whole, and their members are catalogued as
  child items (`archive.zip!member`) so their text is searchable too.

## Use

```bash
export EVI_HOME=~/repo/mom-evi-vault
uv run evi add ~/DOS/MagicExtras --collection magicextras-2001 \
    --source "Kevin's archive, ~/DOS/MagicExtras" --license "third party, unknown"
uv run evi search "wizard NEAR fame"         # SQLite FTS5 syntax
uv run evi show 42                           # provenance and linked claims
uv run evi get 42 -o original.bin            # the exact original bytes
uv run evi claim "Wizard fame is u16 at +0x24" --status checked --reference live-ram-map.md
uv run evi link 1 42 --detail "UGE entry 'Fame' at 0x0A0C"
uv run evi stats
uv run evi verify
uv run evi claim "Fame: u16 at +0x24" --status checked --topic wizard-record
uv run evi link 1 223 --detail "11 after gaining fame" --offset 0x328DE --length 2
uv run evi publish embed --collection mom-live-2026-09-23 --kind image
uv run evi report wizard-record -o reports/wizard-record --title "The wizard record"
uv run --extra ui evi serve                  # browse in Datasette at http://127.0.0.1:8001
```

## Reports

`evi report TOPIC` writes a topic's claims with their evidence as
`report.md`, a printable `report.html` (print it to PDF from a browser)
and `report.wiki` (MediaWiki markup), plus the figures they use. Each
claim lists its sources and shows the exact bytes it rests on.

What a report may carry is set per item with `evi publish`:

| Policy | Reports may |
| --- | --- |
| `embed` | show it in full, e.g. our own screenshots as figures |
| `excerpt` | quote the linked bytes only, at most 64 (RAM dumps: they hold the game's own code and data) |
| `cite` (default) | name it with its provenance, never copy it (third-party files) |
| `never` | name it only (game files) |

## Catalogue

`catalog.sqlite` in the vault:

| Table | What |
| --- | --- |
| `items` | every piece of evidence: hash, size, kind (`ramdump`, `archive`, `image`, `document`, `binary`), storage, provenance, parent, publish policy |
| `texts` | extracted text (FTS5): plain text, HTML, RTF, PDF |
| `claims` | statement, topic, status (`checked` / `guess` / `refuted`), the settling test, where it's written up |
| `claim_evidence` | which items support, contradict or give context to which claim, the detail relied on, and the byte range (`offset`, `length`) |

## Develop

```bash
uv run pytest
```

## Licence

MIT. The licence covers Evi's code only, never the contents of a vault.
