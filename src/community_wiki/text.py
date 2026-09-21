"""Lossless Unicode token windows and local document readers."""

import os
import re
from pathlib import Path

import jieba
import tiktoken

from .config import PDFConfig
from .pdf import PDFParser


class TextProcessor:
    def __init__(self, encoding: str, cache_dir: Path):
        cache_dir.mkdir(parents=True, exist_ok=True)
        os.environ.setdefault("TIKTOKEN_CACHE_DIR", str(cache_dir))
        self.encoding = tiktoken.get_encoding(encoding)

    def count(self, text: str) -> int:
        return len(self.encoding.encode(text, disallowed_special=()))

    def split(self, text: str, limit: int, overlap: int = 0) -> list[str]:
        if not 0 <= overlap < limit:
            raise ValueError("Require 0 <= overlap < limit")
        tokens = self.encoding.encode(text, disallowed_special=())
        # Token boundaries can bisect a UTF-8 character. Only cut on valid boundaries.
        raw = [self.encoding.decode_single_token_bytes(t) for t in tokens]
        offsets = [0]
        for part in raw:
            offsets.append(offsets[-1] + len(part))
        data = text.encode("utf-8")
        valid = {
            i
            for i, offset in enumerate(offsets)
            if offset == len(data) or data[offset] & 0xC0 != 0x80
        }
        result, start = [], 0
        while start < len(tokens):
            end = min(start + limit, len(tokens))
            while end not in valid:
                end -= 1
            if end <= start:
                raise ValueError("Token limit too small to hold one Unicode character")
            result.append(data[offsets[start] : offsets[end]].decode("utf-8"))
            if end == len(tokens):
                break
            next_start = max(start + 1, end - overlap)
            while next_start not in valid:
                next_start += 1
            start = next_start
        return result


def read_document(path: Path, pdf_config: PDFConfig | None = None) -> str:
    if path.suffix.lower() == ".pdf":
        text = PDFParser(pdf_config or PDFConfig()).parse(path)
    else:
        text = path.read_text(encoding="utf-8-sig")
    if not text.strip():
        raise ValueError(f"No extractable text: {path}; scanned PDFs require external OCR")
    return text


def lexical_tokens(text: str) -> list[str]:
    return [t.casefold() for t in jieba.cut(text, HMM=False) if re.search(r"\w", t, re.UNICODE)]
