"""
Extract chapters / sections / chunks from a textbook PDF.

Strategy (heuristic, works on NCERT/state-board style books):
  1. Extract text per page with PyMuPDF.
  2. Drop headers, footers, page numbers.
  3. Detect chapter starts by:
       - "Chapter N" / "अध्याय N" markers, OR
       - Large font (> 15pt) lines near top of page.
  4. Detect section starts inside a chapter by regex: "<n>.<m> Title".
  5. Chunk each section into ~600-token paragraphs.

Everything is best-effort. The teacher reviews and edits before publishing.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF


# ---------------------------------------------------------------
# Data shapes
# ---------------------------------------------------------------

@dataclass
class Chunk:
    text: str
    page: int


@dataclass
class Section:
    number: str
    title: str
    start_page: int
    end_page: int
    chunks: list[Chunk] = field(default_factory=list)


@dataclass
class Chapter:
    number: int
    title: str
    start_page: int
    end_page: int
    sections: list[Section] = field(default_factory=list)


@dataclass
class ParsedBook:
    page_count: int
    chapters: list[Chapter] = field(default_factory=list)


# ---------------------------------------------------------------
# Regexes
# ---------------------------------------------------------------

# "Chapter 4", "CHAPTER 4", "अध्याय 4", "अध्याय-4"
_CHAPTER_RE = re.compile(r"^(?:chapter|अध्याय)[\s\-]*(\d+)\s*[:\-]?\s*(.*)$", re.IGNORECASE)

# "4.2 Something", "4.2. Something", "4.2 - Something"
_SECTION_RE = re.compile(r"^(\d{1,2}\.\d{1,2}(?:\.\d{1,2})?)\s*[\.\-:–]?\s+(.+)$")

# A line that is just a number (page footer)
_PAGE_NUM_RE = re.compile(r"^\s*\d{1,4}\s*$")

# Roman numeral page number
_ROMAN_RE = re.compile(r"^\s*[ivxlc]{1,6}\s*$", re.IGNORECASE)


# ---------------------------------------------------------------
# Page extraction
# ---------------------------------------------------------------

def _extract_page_lines(page: fitz.Page) -> list[dict[str, Any]]:
    """
    Return lines with text, size (max font size in the line), and
    whether the line is at the top of the page.
    """
    page_height = page.rect.height
    top_threshold = page_height * 0.25     # top quartile

    lines: list[dict[str, Any]] = []
    text_dict = page.get_text("dict")
    for block in text_dict.get("blocks", []):
        if block.get("type") != 0:         # only text blocks
            continue
        for line in block.get("lines", []):
            spans = line.get("spans", [])
            if not spans:
                continue
            text = "".join(s.get("text", "") for s in spans).strip()
            if not text:
                continue
            sizes = [s.get("size", 0) for s in spans]
            sizes = [s for s in sizes if s]
            max_size = max(sizes) if sizes else 0
            y0 = line.get("bbox", (0, 0, 0, 0))[1]
            lines.append({
                "text": text,
                "size": max_size,
                "is_top": y0 < top_threshold,
            })
    return lines


def _is_noise(text: str) -> bool:
    if len(text) < 2:
        return True
    if _PAGE_NUM_RE.match(text):
        return True
    if _ROMAN_RE.match(text):
        return True
    return False


# ---------------------------------------------------------------
# Chapter / section detection
# ---------------------------------------------------------------

def _is_chapter_header(line: dict, body_size: float) -> bool:
    """Chapter headers are large and usually near top of page."""
    if _is_noise(line["text"]):
        return False
    # Explicit "Chapter N" or "अध्याय N" — always wins
    if _CHAPTER_RE.match(line["text"]):
        return True
    # Heuristic: big font + top of page + short line
    if line["size"] >= body_size + 3 and line["is_top"] and len(line["text"]) < 80:
        # Skip if it looks like a section header
        if _SECTION_RE.match(line["text"]):
            return False
        # Skip if the line is only a single word in a huge font (title page noise)
        words = line["text"].split()
        if len(words) <= 2 and line["size"] >= 20:
            return False
        return True
    return False


def _body_size(pages: list[list[dict]]) -> float:
    """Estimate the body font size as the most common max-size across pages."""
    from collections import Counter
    counter: Counter[float] = Counter()
    for page_lines in pages:
        for line in page_lines:
            counter[round(line["size"], 1)] += 1
    if not counter:
        return 11.0
    # Most common rounded size
    return counter.most_common(1)[0][0]


# ---------------------------------------------------------------
# Main parse
# ---------------------------------------------------------------

def parse_pdf(pdf_path: str | Path) -> ParsedBook:
    doc = fitz.open(str(pdf_path))
    page_count = doc.page_count

    # Pass 1: extract lines for all pages
    pages_lines: list[list[dict]] = []
    for page in doc:
        pages_lines.append(_extract_page_lines(page))

    body = _body_size(pages_lines)

    # Pass 2: walk pages, detect chapter and section boundaries
    chapters: list[Chapter] = []
    current_chapter: Chapter | None = None
    current_section: Section | None = None
    pending_section_buffer: list[Chunk] = []
    pending_chapter_buffer: list[Chunk] = []   # content before first section

    def _flush_section(end_page: int) -> None:
        nonlocal current_section, pending_section_buffer
        if current_section is not None:
            current_section.end_page = end_page
            current_section.chunks.extend(pending_section_buffer)
            if pending_section_buffer:
                pending_section_buffer = []

    def _flush_chapter(end_page: int) -> None:
        nonlocal current_chapter, pending_chapter_buffer
        if current_chapter is None:
            return
        _flush_section(end_page)
        # If no sections were found, keep pre-section content as one implicit section
        if not current_chapter.sections and pending_chapter_buffer:
            current_chapter.sections.append(Section(
                number=f"{current_chapter.number}.1",
                title="(untitled)",
                start_page=current_chapter.start_page,
                end_page=end_page,
                chunks=list(pending_chapter_buffer),
            ))
            pending_chapter_buffer = []
        current_chapter.end_page = end_page
        chapters.append(current_chapter)
        current_chapter = None

    for page_index, lines in enumerate(pages_lines, start=1):
        for line in lines:
            text = line["text"]

            # Chapter boundary?
            if _is_chapter_header(line, body):
                m = _CHAPTER_RE.match(text)
                if m:
                    num = int(m.group(1))
                    title = (m.group(2) or "").strip()
                else:
                    # Non-"Chapter N" large header → sequential numbering
                    num = (current_chapter.number + 1) if current_chapter else (len(chapters) + 1)
                    title = text.strip()

                # If the title is empty (e.g. just "Chapter 5"), peek at the
                # next non-noise line on the same page
                if not title:
                    for j, nxt in enumerate(lines):
                        if nxt is line and j + 1 < len(lines):
                            for k in range(j + 1, min(j + 4, len(lines))):
                                cand = lines[k]["text"]
                                if not _is_noise(cand) and len(cand) < 80:
                                    title = cand.strip()
                                    break
                            break

                # Close any open chapter
                _flush_chapter(page_index)
                current_chapter = Chapter(
                    number=num, title=title,
                    start_page=page_index, end_page=page_index,
                )
                continue

            # Section boundary?
            m_sec = _SECTION_RE.match(text)
            if m_sec and current_chapter is not None:
                number = m_sec.group(1)
                title = m_sec.group(2).strip()
                # Filter out false positives — e.g. "2.5 million" style
                if len(title) >= 3 and any(c.isalpha() for c in title):
                    _flush_section(page_index)
                    current_section = Section(
                        number=number, title=title,
                        start_page=page_index, end_page=page_index,
                    )
                    current_chapter.sections.append(current_section)
                    continue

            # Otherwise it's content
            if _is_noise(text):
                continue

            chunk = Chunk(text=text, page=page_index)
            if current_section is not None:
                pending_section_buffer.append(chunk)
            elif current_chapter is not None:
                pending_chapter_buffer.append(chunk)

    # Flush the last chapter
    _flush_chapter(page_count)

    # Merge tiny chunks into paragraphs (section-wise)
    for ch in chapters:
        for sec in ch.sections:
            sec.chunks = _merge_into_paragraphs(sec.chunks)

    doc.close()
    return ParsedBook(page_count=page_count, chapters=chapters)


# ---------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------

_TARGET_CHARS = 1800       # ~500-600 tokens
_MAX_CHARS = 2400


def _merge_into_paragraphs(chunks: list[Chunk]) -> list[Chunk]:
    """
    Chunks arrive as individual lines. Merge them into paragraph-sized
    pieces of roughly _TARGET_CHARS.
    """
    merged: list[Chunk] = []
    buffer: list[str] = []
    current_page: int | None = None
    current_len = 0

    def _flush() -> None:
        nonlocal buffer, current_len, current_page
        if buffer:
            text = " ".join(s.strip() for s in buffer if s.strip())
            if text:
                merged.append(Chunk(text=text, page=current_page or 1))
        buffer = []
        current_len = 0
        current_page = None

    for c in chunks:
        if current_page is None:
            current_page = c.page
        buffer.append(c.text)
        current_len += len(c.text) + 1
        if current_len >= _TARGET_CHARS:
            _flush()

    _flush()
    return merged


# ---------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------

def parsed_to_dict(parsed: ParsedBook) -> dict:
    """Convert dataclass tree into plain JSON-serializable dict."""
    return {
        "page_count": parsed.page_count,
        "chapters": [
            {
                "number": ch.number,
                "title": ch.title,
                "start_page": ch.start_page,
                "end_page": ch.end_page,
                "sections": [
                    {
                        "number": s.number,
                        "title": s.title,
                        "start_page": s.start_page,
                        "end_page": s.end_page,
                        "chunks": [asdict(c) for c in s.chunks],
                    }
                    for s in ch.sections
                ],
            }
            for ch in parsed.chapters
        ],
    }
