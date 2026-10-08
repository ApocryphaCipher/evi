# STORY-001: `Claim` and `Evidence` messages, and `evi export`

**Parent:** [EPIC-001](../epics/EPIC-001-protobuf-export.md)
**Status:** Not started. Needs gama's
[STORY-001](https://github.com/ApocryphaCipher/gama/blob/main/docs/stories/STORY-001-create-the-contract-repo.md) (the contract repo).
**Size:** medium

## The idea

A claim, with the evidence for and against it, is the most valuable thing in a
vault, and today it exists only inside SQLite. Write it as protobuf so another
program, or another vault, can read it without Evi's schema.

## The messages

```proto
enum ClaimStatus {
  CLAIM_STATUS_UNSPECIFIED = 0;
  CHECKED = 1;
  GUESS = 2;
  REFUTED = 3;
}

enum EvidenceRole {
  EVIDENCE_ROLE_UNSPECIFIED = 0;
  SUPPORTS = 1;
  CONTRADICTS = 2;
  CONTEXT = 3;
}

enum PublishPolicy {
  PUBLISH_POLICY_UNSPECIFIED = 0;
  EMBED = 1;
  EXCERPT = 2;
  CITE = 3;
  NEVER = 4;
}

message Source {              // an item, by identity and provenance; never its bytes
  string sha256 = 1;
  string name = 2;
  string path = 3;
  string collection = 4;
  string source = 5;
  string author = 6;
  string license = 7;
  PublishPolicy publish = 8;
  google.protobuf.Timestamp file_time = 9;
}

message Evidence {
  Source source = 1;
  EvidenceRole role = 2;
  string detail = 3;
  optional uint64 offset = 4;   // optional: offset 0 is real
  optional uint64 length = 5;
}

message Claim {
  string statement = 1;
  string topic = 2;
  ClaimStatus status = 3;
  string test = 4;              // what would settle a guess
  string reference = 5;
  repeated Evidence evidence = 6;
}

message ClaimSet { repeated Claim claims = 1; }
```

These mirror the `claims`, `claim_evidence` and `items` tables
([vault-layout.md](../reference/vault-layout.md)).

## What changes

`evi export [--topic T] -o claims.pb` writes a `ClaimSet`. The item ids in SQLite
are *not* exported (they mean nothing in another vault); a `Source` is
identified by its `sha256` and `collection` + `path`.

## Acceptance

- Every claim, with all its evidence, in a vault with a few of each status and
  role, round-trips: export, parse with the generated code, and compare each
  field to the SQL rows.
- `offset` of 0 survives (it is present, not absent); a missing `offset` stays
  absent.
- The `ClaimStatus` enum matches the SQL `CHECK` exactly. A test reads the
  allowed values from the schema text and fails if a value is added to one but
  not the other.
- **No blob contents are written**, whatever the publish policy. A test asserts
  that no item's bytes appear in the export.
- Documented in `docs/reference/`.

## Notes

- *Guess:* `uint64` is more than offsets need (a 16 MiB dump fits in 32 bits).
  Use the wider type; the cost is nothing and a larger dump won't need a
  breaking change.
