# STORY-002: `evi import` reads an export

**Parent:** [EPIC-001](../epics/EPIC-001-protobuf-export.md)
**Status:** Not started. Needs [STORY-001](STORY-001-claim-and-evidence-messages.md).
**Size:** medium

## The idea

An export that can't be read back is a report, not a format. `evi import`
loads a `ClaimSet` into a vault, so claims can move between vaults or be
restored. This is also the test that the export lost nothing.

## What changes

`evi import claims.pb` adds each claim and links its evidence to items **already
in the vault**, found by `sha256` plus `collection` and `path`.

The hard question is what to do when an item isn't there. Choose and write down:

1. **Skip the evidence and say so** (recommended): add the claim, report
   "evidence N not linked: no item with that hash", so a claim never points
   at something Evi can't show.
2. Refuse the whole import. Safer, less useful.

A claim is never silently dropped.

## Rules the import must keep

- Status, role and `test` come through exactly. A `GUESS` with no `test` is
  allowed on import (old data), but is reported.
- **The publish policy is not loosened.** The export carries each item's policy
  for information, but import **never changes** an existing item's policy from
  an export: the vault's own setting wins. This is what stops a `never` turning
  into a `cite`.
- Importing the same file twice doesn't duplicate claims. Match an existing
  claim by statement and topic; say "already there".

## Acceptance

- Export from vault A, import into vault B (which holds the same items under the
  same hashes), and the claims and links in B equal A's, field for field.
- The publish-policy rule has its own test.
- A missing item is reported and does not abort the rest.
- Importing twice changes nothing the second time.

## Notes

- A claim's evidence offset and length describe bytes of an item; they are
  meaningful only if B's item has the same hash. The hash match is what makes it
  safe, so never match on name alone.
