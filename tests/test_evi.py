import io
import zipfile

from evi.blobs import PAGE_SIZE, BlobStore, sha256
from evi.vault import Provenance, Vault


def test_paged_storage_round_trips_and_shares_pages(tmp_path):
    store = BlobStore(tmp_path / "blobs")
    first = bytearray(16 * PAGE_SIZE)
    first[5] = 1
    second = bytearray(first)
    second[9 * PAGE_SIZE] = 2

    sha1, manifest1 = store.put_paged(bytes(first))
    before = len(store.all())
    sha2, manifest2 = store.put_paged(bytes(second))

    assert store.get_paged(manifest1) == first and sha1 == sha256(first)
    assert store.get_paged(manifest2) == second and sha2 == sha256(second)
    # One changed page plus the new manifest.
    assert len(store.all()) - before == 2


def make_zip(files: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, data in files.items():
            zf.writestr(name, data)
    return buf.getvalue()


def test_add_catalogues_archive_members_and_text(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "notes.htm").write_bytes(b"<html><body><p>Fame lives at 0A0C</p></body></html>")
    (src / "bundle.zip").write_bytes(make_zip({"README.TXT": b"Hacking the wizard record"}))
    (src / "skip.tmp").write_bytes(b"ignore me")

    vault = Vault(tmp_path / "vault")
    prov = Provenance("test", source="unit test", license="none")
    results = vault.add_path(src, prov, exclude=["*.tmp"])
    assert sum(new for _, _, new in results) == 3  # htm, zip, zip member

    assert [r["path"] for r in vault.catalog.search("wizard")] == [f"{src / 'bundle.zip'}!README.TXT"]
    assert vault.catalog.search("Fame")[0]["path"].endswith("notes.htm")

    again = vault.add_path(src, prov, exclude=["*.tmp"])
    assert not any(new for _, _, new in again)
    assert vault.verify() == []


def test_claims_link_to_evidence(tmp_path):
    src = tmp_path / "a.txt"
    src.write_bytes(b"gold at +0x356")
    vault = Vault(tmp_path / "vault")
    [(item_id, _, _)] = vault.add_path(src, Provenance("test"), exclude=[])

    claim = vault.catalog.add_claim("Wizard gold is u16 at +0x356", "checked", None, "live-ram-map.md")
    vault.catalog.link(claim, item_id, "supports", "+0x356")
    row = vault.catalog.db.execute("SELECT role, detail FROM claim_evidence").fetchone()
    assert (row["role"], row["detail"]) == ("supports", "+0x356")


def test_add_bytes_attaches_to_a_parent(tmp_path):
    vault = Vault(tmp_path / "vault")
    prov = Provenance("live", source="api")
    dump_id = vault.add_bytes(bytes(16 * 1024 * 1024), "cp.bin", "api://memory", prov)
    shot_id = vault.add_bytes(b"\x89PNG fake", "cp.png", "api://screenshot", prov, parent_id=dump_id)
    row = vault.catalog.db.execute("SELECT kind, parent_id FROM items WHERE id = ?", (shot_id,)).fetchone()
    assert (row["kind"], row["parent_id"]) == ("image", dump_id)
    assert vault.catalog.db.execute("SELECT storage FROM items WHERE id = ?", (dump_id,)).fetchone()[0] == "paged"
    assert vault.add_bytes(bytes(16 * 1024 * 1024), "cp.bin", "api://memory", prov) == dump_id


def test_report_respects_publish_policy(tmp_path):
    from evi import report

    src = tmp_path / "src"
    src.mkdir()
    (src / "dump.bin").write_bytes(b"\x00" * 32 + b"Freya\x00" + b"\x00" * (16 * 1024 * 1024 - 38))
    (src / "shot.png").write_bytes(b"\x89PNG fake")
    (src / "notes.txt").write_bytes(b"third-party notes, name at 0x01")
    vault = Vault(tmp_path / "vault")
    vault.add_path(src, Provenance("t", source="test"), exclude=[])
    ids = {r["name"]: r["id"] for r in vault.catalog.db.execute("SELECT id, name FROM items")}
    vault.catalog.set_publish("id = ?", (ids["dump.bin"],), "excerpt")
    vault.catalog.set_publish("id = ?", (ids["shot.png"],), "embed")

    claim = vault.catalog.add_claim("Name at +0x01", "checked", None, None, topic="wiz")
    vault.catalog.link(claim, ids["dump.bin"], "supports", "Freya", offset=32, length=500)
    vault.catalog.link(claim, ids["shot.png"], "supports", "on screen")
    vault.catalog.link(claim, ids["notes.txt"], "supports", "says so", offset=0, length=8)
    vault.catalog.commit()

    out = tmp_path / "out"
    rep = report.write(vault, "wiz", "Wizard", out)
    by_name = {e.source.name: e for e in rep.claims[0].evidence}
    assert len(by_name["dump.bin"].excerpt[1]) == report.MAX_EXCERPT  # capped
    assert by_name["notes.txt"].excerpt is None  # cite only: never quoted
    assert (out / by_name["shot.png"].figure).exists()
    md = (out / "report.md").read_text()
    assert "Freya" in md and "third-party notes" not in md
    assert (out / "report.html").exists() and "== Sources ==" in (out / "report.wiki").read_text()
