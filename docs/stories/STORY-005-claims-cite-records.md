# STORY-005: A claim can rest on a record in a stream

**Parent:** [EPIC-001](../epics/EPIC-001-protobuf-export.md)
**Status:** Not started, stretch. Needs [STORY-003](STORY-003-store-protobuf-streams-as-evidence.md) and [STORY-004](STORY-004-show-decodes-streams.md).
**Size:** medium

## The idea

A claim links to an item and, optionally, to a byte range in it
(`offset`, `length`). For a RAM dump that is exactly right. For a stream of
records, the natural pointer is "record 17", not "bytes 1,204 to 1,512", and a
byte range goes stale if the stream is ever re-encoded. Let the evidence say
which record.

## What changes

- A nullable `record` column on `claim_evidence` (added by `_migrate()`).
- `evi link CLAIM ITEM --record N`. For a `pbstream` item, `--record` and
  `--offset` are alternatives; giving both is an error.
- `evi report` quotes the record, decoded as in
  [STORY-004](STORY-004-show-decodes-streams.md), where it quoted a hex dump of
  the byte range, and **obeys the same policy rules**: `excerpt` allows at most
  64 bytes of any byte field, `never` allows none.
- The export from [STORY-001](STORY-001-claim-and-evidence-messages.md) gains
  `optional uint64 record = 6` on `Evidence`.

## Acceptance

- A claim linked to record 17 of a stream shows record 17 in `report.md`, and
  only that.
- The 64-byte cap is applied to a record's byte fields, with a test.
- A record number past the end of the stream is rejected when linking.
- The export and `evi import` carry `record`.

## Notes

- *Guess:* this story is where the epic stops being a format exercise and starts
  to change how evidence is cited. Do it last, and only if it feels wanted.
