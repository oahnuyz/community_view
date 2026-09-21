"""Local, page-ordered PDF to Markdown; no model calls or implicit OCR."""

import logging
import re
from collections import Counter, defaultdict
from pathlib import Path

from .config import PDFConfig

log = logging.getLogger(__name__)
PARSER_VERSION = "pdfplumber-markdown-v1"


def clean_unicode(text: str, source: str) -> str:
    """Recover surrogate pairs and visibly replace irrecoverable lone surrogates."""
    text, pairs = re.subn(
        r"[\ud800-\udbff][\udc00-\udfff]",
        lambda m: chr(0x10000 + ((ord(m[0][0]) - 0xD800) << 10) + ord(m[0][1]) - 0xDC00),
        text,
    )
    text, isolated = re.subn(r"[\ud800-\udfff]", "\ufffd", text)
    if pairs or isolated:
        log.warning(
            "PDF Unicode repair %s: restored_pairs=%d replaced_lone_surrogates=%d",
            source,
            pairs,
            isolated,
        )
    return text


def normalize_title(text):
    return "".join(c for c in text.casefold() if c.isalnum())


def markdown_table(rows):
    if not rows:
        return ""
    width = max(map(len, rows))
    if not width or not any(str(cell or "").strip() for row in rows for cell in row):
        return ""

    def render(row):
        cells = [
            str(cell or "").replace("\\", "\\\\").replace("|", "\\|").replace("\n", "<br>")
            for cell in row
        ]
        return "| " + " | ".join(cells + [""] * (width - len(cells))) + " |"

    return "\n".join([render(rows[0]), render(["---"] * width), *map(render, rows[1:])])


class PDFParser:
    def __init__(self, config: PDFConfig):
        self.config = config

    def _outlines(self, pdf, path):
        from pdfminer.pdfdocument import PDFNoOutlines
        from pdfminer.pdftypes import PDFObjRef, resolve1
        from pdfminer.utils import decode_text

        result = defaultdict(list)
        page_numbers = {page.page_obj.pageid: page.page_number for page in pdf.pages}
        try:
            for level, title, destination, action, _ in pdf.doc.get_outlines():
                try:
                    if destination is None and action is not None:
                        destination = resolve1(action).get("D")
                    if isinstance(destination, (str, bytes)):
                        destination = pdf.doc.get_dest(destination)
                    destination = resolve1(destination)
                    if isinstance(destination, dict):
                        destination = resolve1(destination.get("D"))
                    if not isinstance(destination, (list, tuple)) or not destination:
                        continue
                    ref = destination[0]
                    number = page_numbers.get(ref.objid) if isinstance(ref, PDFObjRef) else None
                    if number is None:
                        continue
                    title = decode_text(title) if isinstance(title, bytes) else str(title)
                    title = clean_unicode(title, f"{path} bookmark").strip()
                    if title:
                        result[number].append(
                            (min(max(level, 1), self.config.max_heading_level), title)
                        )
                except (KeyError, TypeError, ValueError, AttributeError) as exc:
                    log.warning("PDF bookmark skipped %s: %s", path, exc)
        except PDFNoOutlines:
            pass
        except Exception as exc:
            log.warning("PDF bookmarks unavailable %s: %s", path, exc)
        return result

    def _font_headings(self, page):
        sizes = Counter()
        for char in page.chars:
            if char.get("text", "").strip():
                sizes[round(float(char.get("size", 0)), 1)] += len(char["text"])
        if not sizes:
            return []
        body = sizes.most_common(1)[0][0]
        candidates = []
        for line in page.extract_text_lines(return_chars=True):
            title = line["text"].strip()
            chars = [c for c in line["chars"] if c.get("text", "").strip()]
            if not title or len(title) > self.config.heading_max_chars or not chars:
                continue
            # Majority size prevents an oversized equation symbol from marking a whole line.
            size = Counter(round(float(c.get("size", 0)), 1) for c in chars).most_common(1)[0][0]
            if size >= body * self.config.heading_min_size_ratio and any(
                c.isalpha() for c in title
            ):
                candidates.append((size, title))
        levels = {
            size: min(i, self.config.max_heading_level)
            for i, size in enumerate(sorted({c[0] for c in candidates}, reverse=True), 1)
        }
        return [(levels[size], title) for size, title in candidates]

    @staticmethod
    def _mark_headings(text, headings, *, append_unmatched):
        lines = text.splitlines()
        unmatched = []
        for level, title in headings:
            key = normalize_title(title)
            if not key:
                continue
            for i, line in enumerate(lines):
                if normalize_title(line) == key:
                    lines[i] = "#" * level + " " + line.lstrip("# ")
                    break
            else:
                if append_unmatched:
                    unmatched.append("#" * level + " " + title)
        return "\n".join([*unmatched, *lines])

    def parse(self, path: Path) -> str:
        import pdfplumber

        parts, has_content = [], False
        with pdfplumber.open(path) as pdf:
            outlines = self._outlines(pdf, path)
            for page in pdf.pages:
                source = f"{path} page={page.page_number}"
                try:
                    text = clean_unicode(page.extract_text() or "", source)
                    has_content |= bool(text.strip())
                    headings = outlines.get(page.page_number, [])
                    if not outlines:
                        headings = self._font_headings(page)
                    text = self._mark_headings(text, headings, append_unmatched=bool(outlines))
                    tables = []
                    if self.config.extract_tables:
                        try:
                            tables = [
                                markdown_table(rows)
                                for rows in page.extract_tables(
                                    table_settings=self.config.table_settings
                                )
                            ]
                        except Exception as exc:
                            log.warning(
                                "PDF table extraction failed %s: %s; retaining text", source, exc
                            )
                    has_content |= any(tables)
                    if not text.strip() and not any(tables):
                        log.warning("PDF page has no extractable text %s; no OCR performed", source)
                    parts.append(
                        clean_unicode(
                            "\n\n".join(
                                [f"<!-- Page {page.page_number} -->", text, *filter(None, tables)]
                            ),
                            source,
                        )
                    )
                except Exception as exc:
                    raise ValueError(f"PDF parsing failed {source}: {exc}") from exc
                finally:
                    page.close()
        if not has_content:
            raise ValueError(f"No extractable text: {path}; scanned PDFs require external OCR")
        return "\n\n".join(parts)
