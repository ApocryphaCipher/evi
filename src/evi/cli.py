"""evi command line."""

import argparse
import os
import subprocess
import sys
from pathlib import Path

from evi.report import write as write_report
from evi.vault import Provenance, Vault


def cmd_add(vault: Vault, args) -> None:
    prov = Provenance(args.collection, args.source, args.author, args.license, args.note)
    new = seen = 0
    for path in args.paths:
        for item_id, item_path, was_new in vault.add_path(Path(path), prov, args.exclude or []):
            new += was_new
            seen += not was_new
            if args.verbose:
                print(f"{item_id:6}  {'added' if was_new else 'known'}  {item_path}")
    print(f"{new} items added, {seen} already catalogued")


def cmd_search(vault: Vault, args) -> None:
    for row in vault.catalog.search(args.query, args.limit):
        print(f"{row['id']:6}  {row['collection']}  {row['path']}\n        {row['hit']}")


def cmd_show(vault: Vault, args) -> None:
    db = vault.catalog.db
    item = db.execute("SELECT * FROM items WHERE id = ?", (args.item,)).fetchone()
    if item is None:
        sys.exit(f"evi: no item {args.item}")
    for key in item.keys():
        if item[key] is not None:
            print(f"{key:16} {item[key]}")
    for row in db.execute(
        "SELECT c.id, c.status, c.statement, e.role, e.detail FROM claim_evidence e"
        " JOIN claims c ON c.id = e.claim_id WHERE e.item_id = ?", (args.item,)
    ):
        print(f"claim {row['id']} ({row['status']}, {row['role']}): {row['statement']}"
              + (f"  [{row['detail']}]" if row["detail"] else ""))


def cmd_get(vault: Vault, args) -> None:
    data = vault.original(args.item)
    if args.out:
        Path(args.out).write_bytes(data)
    else:
        sys.stdout.buffer.write(data)


def cmd_claim(vault: Vault, args) -> None:
    claim_id = vault.catalog.add_claim(args.statement, args.status, args.test, args.reference, args.topic)
    vault.catalog.commit()
    print(f"claim {claim_id}")


def cmd_link(vault: Vault, args) -> None:
    vault.catalog.link(args.claim, args.item, args.role, args.detail, args.offset, args.length)
    vault.catalog.commit()


def cmd_publish(vault: Vault, args) -> None:
    if args.items:
        marks = ", ".join("?" * len(args.items))
        count = vault.catalog.set_publish(f"id IN ({marks})", tuple(args.items), args.policy)
    else:
        where, params = "collection = ?", [args.collection]
        if args.kind:
            where += " AND kind = ?"
            params.append(args.kind)
        count = vault.catalog.set_publish(where, tuple(params), args.policy)
    vault.catalog.commit()
    print(f"{count} items set to '{args.policy}'")


def cmd_report(vault: Vault, args) -> None:
    out = Path(args.out)
    report = write_report(vault, args.topic, args.title or args.topic, out)
    print(f"{len(report.claims)} claims, {len(report.sources)} sources -> {out}/report.{{md,html,wiki}}")


def cmd_claims(vault: Vault, _args) -> None:
    rows = vault.catalog.db.execute(
        "SELECT c.id, c.status, c.statement, count(e.item_id) AS evidence FROM claims c"
        " LEFT JOIN claim_evidence e ON e.claim_id = c.id GROUP BY c.id ORDER BY c.id"
    )
    for row in rows:
        print(f"{row['id']:4}  {row['status']:8} {row['evidence']} items  {row['statement']}")


def cmd_verify(vault: Vault, _args) -> None:
    problems = vault.verify()
    for problem in problems:
        print(problem)
    count = vault.catalog.db.execute("SELECT count(*) FROM items").fetchone()[0]
    print(f"{count} items checked, {len(problems)} problems")
    if problems:
        sys.exit(1)


def cmd_stats(vault: Vault, _args) -> None:
    db = vault.catalog.db
    for row in db.execute(
        "SELECT collection, kind, count(*) AS n, sum(size) AS bytes FROM items"
        " GROUP BY collection, kind ORDER BY collection, kind"
    ):
        print(f"{row['collection']:28} {row['kind']:9} {row['n']:6} items {row['bytes'] / 2**20:9.1f} MB")
    stored = sum(p.stat().st_size for p in (vault.home / "blobs").glob("*/*.zst"))
    print(f"blob store on disk: {stored / 2**20:.1f} MB")


def cmd_serve(vault: Vault, args) -> None:
    subprocess.run(["datasette", str(vault.home / "catalog.sqlite"), "--port", str(args.port)], check=True)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="evi", description="Evidence store and catalogue")
    parser.add_argument("--home", type=Path, help="vault directory (default $EVI_HOME)")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("add", help="add files or directory trees to the vault")
    p.add_argument("paths", nargs="+")
    p.add_argument("--collection", required=True, help="the batch these belong to")
    p.add_argument("--source", help="where they came from")
    p.add_argument("--author")
    p.add_argument("--license", help="what may be done with them")
    p.add_argument("--note")
    p.add_argument("--exclude", action="append", help="glob of paths to skip (repeatable)")
    p.add_argument("-v", "--verbose", action="store_true")
    p.set_defaults(func=cmd_add)

    p = sub.add_parser("search", help="full-text search of extracted text")
    p.add_argument("query")
    p.add_argument("--limit", type=int, default=20)
    p.set_defaults(func=cmd_search)

    p = sub.add_parser("show", help="an item's provenance and the claims it backs")
    p.add_argument("item", type=int)
    p.set_defaults(func=cmd_show)

    p = sub.add_parser("get", help="write an item's original bytes")
    p.add_argument("item", type=int)
    p.add_argument("-o", "--out")
    p.set_defaults(func=cmd_get)

    p = sub.add_parser("claim", help="record a claim")
    p.add_argument("statement")
    p.add_argument("--status", required=True, choices=["checked", "guess", "refuted"])
    p.add_argument("--test", help="what would settle it")
    p.add_argument("--reference", help="where it's written up")
    p.add_argument("--topic", help="the report it belongs to")
    p.set_defaults(func=cmd_claim)

    p = sub.add_parser("link", help="link an item to a claim as evidence")
    p.add_argument("claim", type=int)
    p.add_argument("item", type=int)
    p.add_argument("--role", default="supports", choices=["supports", "contradicts", "context"])
    p.add_argument("--detail", help="the offset, screen text etc. relied on")
    p.add_argument("--offset", type=lambda v: int(v, 0), help="start of the bytes relied on (e.g. 0x328DE)")
    p.add_argument("--length", type=lambda v: int(v, 0), help="how many bytes (reports quote at most 64)")
    p.set_defaults(func=cmd_link)

    p = sub.add_parser("publish", help="set what reports may do with items: embed, excerpt, cite, never")
    p.add_argument("policy", choices=["embed", "excerpt", "cite", "never"])
    p.add_argument("--items", type=int, nargs="+")
    p.add_argument("--collection")
    p.add_argument("--kind")
    p.set_defaults(func=cmd_publish)

    p = sub.add_parser("report", help="write a topic's claims and evidence as Markdown, HTML and MediaWiki")
    p.add_argument("topic")
    p.add_argument("-o", "--out", required=True, help="output directory")
    p.add_argument("--title")
    p.set_defaults(func=cmd_report)

    sub.add_parser("claims", help="list claims").set_defaults(func=cmd_claims)
    sub.add_parser("verify", help="re-hash every item").set_defaults(func=cmd_verify)
    sub.add_parser("stats", help="counts and sizes").set_defaults(func=cmd_stats)

    p = sub.add_parser("serve", help="browse the catalogue in Datasette (needs the ui extra)")
    p.add_argument("--port", type=int, default=8001)
    p.set_defaults(func=cmd_serve)

    args = parser.parse_args(argv)
    home = args.home or (Path(os.environ["EVI_HOME"]) if "EVI_HOME" in os.environ else None)
    if home is None:
        sys.exit("evi: say which vault: set EVI_HOME or pass --home")
    args.func(Vault(home), args)


if __name__ == "__main__":
    main()
