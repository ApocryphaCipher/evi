# STORY-003: Protobuf streams as a kind of evidence

**Parent:** [EPIC-001](../epics/EPIC-001-protobuf-export.md)
**Status:** Not started. Needs gama's
[STORY-001](https://github.com/ApocryphaCipher/gama/blob/main/docs/stories/STORY-001-create-the-contract-repo.md).
**Size:** medium

## The idea

The fork can write a stream of `SignatureHit` or `Viewport` records, and gama's
`watch` files a session's stream in the vault. Today Evi would store such a file as
a `binary` blob: kept, hashed, but opaque. Make it a first-class kind, so the
catalogue knows what it is and how many records it holds.

## What changes

- A new item `kind`, working name `pbstream`, detected by the file name's suffix
  (`.pb`) **or** by being added with an explicit type.
- A new nullable column on `items`, `message_type` (for example
  `apocrypha.v1.SignatureHit`), added by `_migrate()` like the earlier columns.
  A `.pb` file can't say what it holds, so the type comes from the caller
  (`evi add --message-type apocrypha.v1.SignatureHit`).
- At add time, count the records by walking the length prefixes only (no schema
  needed), and store the count in the item's note or a column.
  A file whose prefixes don't line up exactly with its length is rejected, with
  the offset of the first bad record. Evi does not store a stream it cannot walk.
- Stored whole, as a blob.
- **The default publish policy for a `pbstream` is `never`**, not `cite`: these
  streams hold windows of a game's own memory. Setting it to anything else is an
  explicit `evi publish`.

## Acceptance

- `evi add hits.pb --collection ... --message-type apocrypha.v1.SignatureHit`
  catalogues one item of kind `pbstream`, with a record count.
- A stream truncated mid-record is rejected with a clear message.
- The default policy is `never` (checked by a test).
- `evi verify` handles the new kind unchanged (it is a plain blob).
- `evi stats` counts them separately.
- An older catalogue opens and migrates; items of other kinds are untouched.
- Documented in `vault-layout.md`'s kinds table.

## Notes

- Walking a varint-length-prefixed stream is a few lines and needs no protobuf
  library, which keeps Evi's dependencies as they are.
- Whether a very long stream should be paged like a RAM dump is a later
  question. *Guess:* not worth it; streams are small next to a 16 MiB dump.
