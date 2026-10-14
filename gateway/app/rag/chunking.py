from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Literal

ChunkStrategy = Literal["fixed", "paragraph", "markdown", "openapi"]


@dataclass
class ChunkPreview:
    index: int
    text: str
    char_count: int
    start: int
    end: int
    section: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


STRATEGIES: list[dict] = [
    {"id": "fixed", "label": "固定窗口", "desc": "按字符长度滑动切分，可配置 size / overlap"},
    {"id": "paragraph", "label": "段落", "desc": "按空行分段，过长段落再按固定窗口切开"},
    {"id": "markdown", "label": "Markdown 标题", "desc": "按 # / ## / ### 分块，适合需求文档"},
    {"id": "openapi", "label": "接口文档", "desc": "按路径 / HTTP 方法块切分，适合 OpenAPI / 接口说明"},
]


def preview_chunks(
    text: str,
    strategy: str = "fixed",
    size: int = 400,
    overlap: int = 40,
) -> list[ChunkPreview]:
    text = (text or "").replace("\r\n", "\n")
    if not text.strip():
        return []
    size = max(64, min(int(size or 400), 4000))
    overlap = max(0, min(int(overlap or 0), size - 1))

    if strategy == "paragraph":
        parts = _split_paragraphs(text, size, overlap)
    elif strategy == "markdown":
        parts = _split_markdown(text, size, overlap)
    elif strategy == "openapi":
        parts = _split_openapi(text, size, overlap)
    else:
        parts = _split_fixed(text, size, overlap)

    return [
        ChunkPreview(index=i, text=p["text"], char_count=len(p["text"]), start=p["start"], end=p["end"], section=p.get("section") or "")
        for i, p in enumerate(parts)
    ]


def chunk_texts(text: str, strategy: str = "fixed", size: int = 400, overlap: int = 40) -> list[str]:
    return [c.text for c in preview_chunks(text, strategy=strategy, size=size, overlap=overlap)]


def _split_fixed(text: str, size: int, overlap: int) -> list[dict]:
    out: list[dict] = []
    i = 0
    step = max(1, size - overlap)
    while i < len(text):
        end = min(len(text), i + size)
        piece = text[i:end].strip()
        if piece:
            out.append({"text": piece, "start": i, "end": end, "section": ""})
        if end >= len(text):
            break
        i += step
    return out


def _split_paragraphs(text: str, size: int, overlap: int) -> list[dict]:
    out: list[dict] = []
    for m in re.finditer(r"(?:\S(?:.|\n)*?)(?:\n\s*\n|$)", text):
        block = m.group(0)
        start = m.start()
        if len(block.strip()) <= size:
            if block.strip():
                out.append({"text": block.strip(), "start": start, "end": m.end(), "section": "paragraph"})
        else:
            for p in _split_fixed(block, size, overlap):
                out.append({**p, "start": start + p["start"], "end": start + p["end"], "section": "paragraph"})
    return out or _split_fixed(text, size, overlap)


def _split_markdown(text: str, size: int, overlap: int) -> list[dict]:
    pattern = re.compile(r"(?m)^(#{1,6}\s+.+)$")
    indices = [m.start() for m in pattern.finditer(text)]
    if not indices:
        return _split_paragraphs(text, size, overlap)
    indices.append(len(text))
    out: list[dict] = []
    # preface before first heading
    if indices[0] > 0:
        preface = text[: indices[0]]
        for p in _split_fixed(preface, size, overlap):
            out.append({**p, "section": "preface"})
    for a, b in zip(indices[:-1], indices[1:]):
        block = text[a:b]
        heading = block.split("\n", 1)[0].strip()
        if len(block.strip()) <= size:
            out.append({"text": block.strip(), "start": a, "end": b, "section": heading[:80]})
        else:
            for p in _split_fixed(block, size, overlap):
                out.append({**p, "start": a + p["start"], "end": a + p["end"], "section": heading[:80]})
    return out


def _split_openapi(text: str, size: int, overlap: int) -> list[dict]:
    # Path-like blocks: "## GET /users" or "GET /users" or "  /pet:" yaml paths
    pattern = re.compile(
        r"(?m)^(?:#{1,6}\s+)?(?:(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)\s+)?(/[^\s]+)\s*$"
        r"|^(?m)^\s{0,2}(/[A-Za-z0-9_{}\-./]+)\s*:\s*$"
    )
    matches = list(pattern.finditer(text))
    if not matches:
        return _split_markdown(text, size, overlap)
    starts = [m.start() for m in matches] + [len(text)]
    out: list[dict] = []
    if starts[0] > 0:
        for p in _split_fixed(text[: starts[0]], size, overlap):
            out.append({**p, "section": "preface"})
    for i, m in enumerate(matches):
        a, b = starts[i], starts[i + 1]
        block = text[a:b].strip()
        section = m.group(0).strip()[:80]
        if len(block) <= size:
            out.append({"text": block, "start": a, "end": b, "section": section})
        else:
            for p in _split_fixed(block, size, overlap):
                out.append({**p, "start": a + p["start"], "end": a + p["end"], "section": section})
    return out
