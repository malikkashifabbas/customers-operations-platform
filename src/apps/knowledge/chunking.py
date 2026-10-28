"""Split a policy Markdown file into searchable chunks: one per "##" section, long sections split by paragraph.

Every chunk starts with "<document title> › <section>" so a chunk read on its own still says what it is about.
"""

import re
from dataclasses import dataclass

MAX_CHUNK_CHARS = 1400


@dataclass(frozen=True)
class ParsedDocument:
    title: str
    version: str
    chunks: list["Chunk"]


@dataclass(frozen=True)
class Chunk:
    section: str
    text: str


def _paragraphs(body: str) -> list[str]:
    # A Markdown table has no blank lines inside, so splitting on blank lines never cuts a table in half.
    return [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]


def _pack(paragraphs: list[str]) -> list[str]:
    parts, current = [], ""
    for paragraph in paragraphs:
        if current and len(current) + len(paragraph) + 2 > MAX_CHUNK_CHARS:
            parts.append(current)
            current = paragraph
        else:
            current = f"{current}\n\n{paragraph}" if current else paragraph
    if current:
        parts.append(current)
    return parts


def parse_markdown(markdown: str) -> ParsedDocument:
    lines = markdown.strip().splitlines()
    title = lines[0].lstrip("# ").strip() if lines and lines[0].startswith("# ") else "Untitled"
    version = next((line.strip() for line in lines[1:6] if line.strip().startswith("Effective:")), "")

    sections: list[tuple[str, str]] = []
    heading, buffer = "Overview", []
    for line in lines[1:]:
        if line.startswith("## "):
            sections.append((heading, "\n".join(buffer)))
            heading, buffer = line[3:].strip(), []
        else:
            buffer.append(line)
    sections.append((heading, "\n".join(buffer)))

    chunks = [
        Chunk(section=name, text=f"{title} › {name}\n{part}")
        for name, body in sections
        for part in _pack(_paragraphs(body))
    ]
    return ParsedDocument(title=title, version=version, chunks=chunks)
