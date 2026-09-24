"""Turn files into searchable text, and archives into their members."""

import io
import re
import zipfile
from html.parser import HTMLParser

from pypdf import PdfReader
from striprtf.striprtf import rtf_to_text

TEXT_SUFFIXES = {".txt", ".json", ".doc", ".diz", ".md", ".lst", ".nfo", ".cfg", ".bat", ".momod", ".mommod"}
HTML_SUFFIXES = {".htm", ".html"}
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".pcx"}
ARCHIVE_SUFFIXES = {".zip"}

RAM_DUMP_SIZE = 16 * 1024 * 1024


def kind_of(name: str, size: int) -> str:
    suffix = "." + name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if suffix == ".bin" and size == RAM_DUMP_SIZE:
        return "ramdump"
    if suffix in ARCHIVE_SUFFIXES:
        return "archive"
    if suffix in IMAGE_SUFFIXES:
        return "image"
    if suffix in TEXT_SUFFIXES | HTML_SUFFIXES | {".rtf", ".pdf"}:
        return "document"
    return "binary"


class _TextOnly(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self._skip += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self._skip:
            self._skip -= 1

    def handle_data(self, data):
        if not self._skip:
            self.parts.append(data)


def _decode(data: bytes) -> str:
    # DOS-era text is mostly code page 437; latin-1 never fails and keeps ASCII.
    return data.decode("latin-1")


def _looks_like_text(data: bytes) -> bool:
    sample = data[:4096]
    if not sample:
        return False
    printable = sum(32 <= b < 127 or b in (9, 10, 13) for b in sample)
    return printable / len(sample) > 0.9


def text_of(name: str, data: bytes) -> str | None:
    """Best-effort text of a file, or None when there is nothing to read."""
    suffix = "." + name.rsplit(".", 1)[-1].lower() if "." in name else ""
    try:
        if suffix in HTML_SUFFIXES:
            parser = _TextOnly()
            parser.feed(_decode(data))
            text = " ".join(parser.parts)
        elif suffix == ".rtf":
            text = rtf_to_text(_decode(data))
        elif suffix == ".pdf":
            reader = PdfReader(io.BytesIO(data))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
        elif suffix in TEXT_SUFFIXES or _looks_like_text(data):
            text = _decode(data)
        else:
            return None
    except Exception:
        return None
    text = re.sub(r"[ \t]+", " ", text).strip()
    return text or None


def archive_members(data: bytes) -> list[tuple[str, bytes]]:
    """(path, bytes) for each file in a zip; empty if it can't be read."""
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            return [(info.filename, zf.read(info)) for info in zf.infolist() if not info.is_dir()]
    except (zipfile.BadZipFile, NotImplementedError, RuntimeError):
        return []
