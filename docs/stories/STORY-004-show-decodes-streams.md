# STORY-004: `evi show --decode`

**Parent:** [EPIC-001](../epics/EPIC-001-protobuf-export.md)
**Status:** Not started, stretch. Needs [STORY-003](STORY-003-store-protobuf-streams-as-evidence.md).
**Size:** small to medium

## The idea

A protobuf stream isn't human-readable, which is the cost of the format. Give
`evi show` a way to print the records of a stored `pbstream` item as text, using
the message type recorded when it was added. `protoc --decode` does this by hand;
this makes it one command inside the tool that knows the type.

## What changes

`evi show 42 --decode [--from N] [--count M]` prints records N to N+M−1 in
protobuf's text format, one block per record, with the record index. Evi's
`message_type` column picks the message class from the installed contract
package.

If the contract package isn't installed, or doesn't know the type, say so and
print the raw record sizes instead; don't fail.

## Acceptance

- On a stream of known synthetic records, `--decode` prints each one, and
  `--from` and `--count` select the right slice.
- A bytes field (such as a memory window) is printed as hex, truncated to
  a sane length per record, with its full length shown. **Honour the publish
  policy**: for an item whose policy is `never`, print the structure and sizes
  but not byte contents.
- No contract installed: a clear message, exit code non-zero.

## Notes

- This makes the contract package a (soft) dependency of Evi. Make it optional,
  in an extra like `ui`, so a plain `evi` install stays light.
