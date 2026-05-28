#!/usr/bin/env python3
"""Local persistent memory store for JARVIS.

This is the Phase 2 memory foundation: a lightweight SQLite-backed store that
can hold research findings, planning notes, and reusable context now, while
leaving room to swap in a vector database later.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import chroma_client
import embedding_client


DB_PATH = Path(__file__).resolve().parent.parent / "memory" / "sqlite" / "jarvis.db"
OBSIDIAN_VAULT = Path(__file__).resolve().parent.parent / "memory" / "obsidian-vault"

SCHEMA = """
CREATE TABLE IF NOT EXISTS memory_notes (
    note_id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    source_type TEXT NOT NULL,
    source_ref TEXT NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    tags_json TEXT NOT NULL DEFAULT '[]',
    embedding_json TEXT NOT NULL DEFAULT '[]',
    confidence REAL NOT NULL DEFAULT 0.5
);

CREATE INDEX IF NOT EXISTS idx_memory_notes_source_ref ON memory_notes(source_ref);
CREATE INDEX IF NOT EXISTS idx_memory_notes_created_at ON memory_notes(created_at);
CREATE INDEX IF NOT EXISTS idx_memory_notes_title ON memory_notes(title);
"""


@dataclass(frozen=True)
class MemoryNote:
    note_id: int | None
    created_at: str
    updated_at: str
    source_type: str
    source_ref: str
    title: str
    content: str
    tags: list[str]
    embedding: list[float]
    confidence: float


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def connect(db_path: Path = DB_PATH) -> sqlite3.Connection:
    os.makedirs(db_path.parent, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    conn.commit()
    return conn


def _normalize_embedding(text: str) -> list[float]:
    """Return an embedding vector from the configured backend.

    Uses Ollama with nomic-embed-text when available, falls back to a
    deterministic 3-element signal if the embedding service is unreachable.
    """

    return embedding_client.embed_text(text)


def _chroma_payload(note: MemoryNote) -> tuple[str, list[str], list[dict[str, object]], list[list[float]]]:
    note_id = str(note.note_id or f"{note.source_type}:{note.source_ref}")
    document = f"{note.title}\n\n{note.content}"
    metadata = [
        {
            "note_id": note.note_id,
            "created_at": note.created_at,
            "updated_at": note.updated_at,
            "source_type": note.source_type,
            "source_ref": note.source_ref,
            "title": note.title,
            "tags": note.tags,
            "confidence": note.confidence,
        }
    ]
    embedding = [note.embedding]
    return note_id, [document], metadata, embedding


def _try_store_in_chroma(note: MemoryNote) -> bool:
    if os.getenv("CHROMA_ENABLE", "false").lower() not in {"1", "true", "yes", "on"}:
        return False
    client = chroma_client.ChromaClient()
    try:
        if not client.health():
            return False
        note_id, documents, metadatas, embeddings = _chroma_payload(note)
        client.upsert([note_id], documents, metadatas, embeddings)
        return True
    except Exception:
        return False


def _load_note(row: sqlite3.Row) -> MemoryNote:
    return MemoryNote(
        note_id=row["note_id"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        source_type=row["source_type"],
        source_ref=row["source_ref"],
        title=row["title"],
        content=row["content"],
        tags=json.loads(row["tags_json"]),
        embedding=json.loads(row["embedding_json"]),
        confidence=float(row["confidence"]),
    )


def store_note(
    title: str,
    content: str,
    source_type: str,
    source_ref: str,
    tags: Iterable[str] | None = None,
    confidence: float = 0.5,
    db_path: Path = DB_PATH,
) -> MemoryNote:
    created_at = now_iso()
    embedding = _normalize_embedding(f"{title}\n{content}")
    conn = connect(db_path)
    try:
        conn.execute(
            """
            INSERT INTO memory_notes (
                created_at, updated_at, source_type, source_ref, title, content,
                tags_json, embedding_json, confidence
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                created_at,
                created_at,
                source_type,
                source_ref,
                title,
                content,
                json.dumps(sorted(set(tags or []))),
                json.dumps(embedding),
                confidence,
            ),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM memory_notes WHERE rowid = last_insert_rowid()").fetchone()
        note = _load_note(row)
        _try_store_in_chroma(note)
        return note
    finally:
        conn.close()


def list_notes(limit: int = 20, db_path: Path = DB_PATH) -> list[MemoryNote]:
    conn = connect(db_path)
    try:
        rows = conn.execute(
            "SELECT * FROM memory_notes ORDER BY created_at DESC, note_id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [_load_note(row) for row in rows]
    finally:
        conn.close()


def search_notes(query: str, limit: int = 10, db_path: Path = DB_PATH) -> list[MemoryNote]:
    query_terms = [term for term in query.lower().split() if term]
    conn = connect(db_path)
    try:
        rows = conn.execute("SELECT * FROM memory_notes ORDER BY created_at DESC").fetchall()
        scored: list[tuple[float, sqlite3.Row]] = []
        for row in rows:
            haystack = f"{row['title']} {row['content']} {' '.join(json.loads(row['tags_json']))}".lower()
            score = sum(1 for term in query_terms if term in haystack)
            if score:
                scored.append((float(score), row))
        scored.sort(key=lambda item: (item[0], item[1]["created_at"]), reverse=True)
        return [_load_note(row) for _, row in scored[:limit]]
    finally:
        conn.close()


def chroma_available() -> bool:
    if os.getenv("CHROMA_ENABLE", "false").lower() not in {"1", "true", "yes", "on"}:
        return False
    try:
        return chroma_client.ChromaClient().health()
    except Exception:
        return False


def export_to_obsidian(note: MemoryNote, vault_path: Path = OBSIDIAN_VAULT) -> Path:
    vault_path.mkdir(parents=True, exist_ok=True)
    safe_title = " ".join(part for part in note.title.strip().split()) or f"note-{note.note_id or 'new'}"
    filename = (
        safe_title.replace("/", "-")
        .replace("\\", "-")
        .replace(":", "-")
        .replace("*", "-")
        .replace("?", "-")
        .replace('"', "-")
        .replace("<", "-")
        .replace(">", "-")
        .replace("|", "-")
    ) + ".md"
    filename = re.sub(r"\s+-\s+", " - ", filename)
    filename = re.sub(r"\s+", " ", filename).strip()
    target = vault_path / filename
    markdown = [
        f"# {note.title}",
        "",
        f"- source_type: {note.source_type}",
        f"- source_ref: {note.source_ref}",
        f"- confidence: {note.confidence}",
        f"- tags: {', '.join(note.tags) if note.tags else ''}",
        "",
        note.content,
        "",
    ]
    target.write_text("\n".join(markdown), encoding="utf-8")
    return target
