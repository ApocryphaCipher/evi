# EPIC-001: Protobuf export

**Status:** Proposed (2026-10-08). Not started.
**Requested by:** [Kevin](https://github.com/KevinAsbury), 2026-10-08, "for funsies":
a play project turning the Apocrypha tools into protobuf versions.
**Sibling epics:** [fork EPIC-001](https://github.com/ApocryphaCipher/dosbox-staging/blob/webserver-write-guard/docs/apocrypha/epics/EPIC-001-protobuf-output.md),
[gama EPIC-001](https://github.com/ApocryphaCipher/gama/blob/main/docs/epics/EPIC-001-protobuf-pipeline.md)

## Goal

Give Evi's two kinds of knowledge a typed, portable form: **claims with their
evidence**, and **streams of observations** (the fork's hit and viewport
streams) kept as evidence. Evi is the smallest of the three tools in this epic,
and the one where protobuf's type system says something real: a claim's status
is a three-valued enum, and the rule "a guess names the test that would settle
it" is a thing a schema can state.

This is a learning and tidiness project. SQLite stays the catalogue.

## Decisions made

- **SQLite stays.** Nothing here replaces `catalog.sqlite` or the blob store.
  Protobuf is an *export and import* format and a kind of stored evidence.
- **Same contract as the others.** Messages live in the shared contract repo
  that gama's [STORY-001](https://github.com/ApocryphaCipher/gama/blob/main/docs/stories/STORY-001-create-the-contract-repo.md)
  creates. Evi pins a version.
- **Enums carry the rules.** `ClaimStatus` (`CHECKED`, `GUESS`, `REFUTED`) and
  `PublishPolicy` (`EMBED`, `EXCERPT`, `CITE`, `NEVER`) mirror the SQL checks
  and the README's table. Value 0 of each is `..._UNSPECIFIED`, as protobuf
  expects, and is never written.
- **A vault is never exported whole.** It holds other people's files and game
  data. Exports carry catalogue facts (claims, links, provenance), never blob
  contents, unless a story says otherwise and the publish policy allows it.
- **Game-agnostic.** No message names a game.

## Stories, in order

1. [STORY-001](../stories/STORY-001-claim-and-evidence-messages.md): `Claim` and `Evidence` messages and `evi export`
2. [STORY-002](../stories/STORY-002-import-claims.md): `evi import` reads an export, for moving claims between vaults
3. [STORY-003](../stories/STORY-003-store-protobuf-streams-as-evidence.md): protobuf streams as a kind of evidence
4. [STORY-004](../stories/STORY-004-show-decodes-streams.md): `evi show --decode` (stretch)
5. [STORY-005](../stories/STORY-005-claims-cite-records.md): a claim can rest on a record in a stream (stretch)

## Out of scope

- Replacing `catalog.sqlite` or the blob format with protobuf.
- Exporting item contents, i.e. a way to ship a vault.
- Anything that lets an original change.
- A gRPC service. That is gama's STORY-006.

## Risks

- **Schema drift between the SQL checks and the enums.** If someone adds a
  claim status in SQL and not in the `.proto`, the export breaks or lies. The
  tests in STORY-001 should fail when the two disagree.
- **`license` and the publish policy must survive the round trip.** An export
  that drops them would let a re-import turn a `never` into a `cite`. STORY-002
  tests this explicitly.
