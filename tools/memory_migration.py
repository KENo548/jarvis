#!/usr/bin/env python3
"""Migrate Mark XXXIX JSON memory to SAGE's Chroma + SQLite.

Usage:
    python migrate_memory.py                    # Dry run (show what would migrate)
    python migrate_memory.py --execute          # Actually migrate
    python migrate_memory.py --source PATH      # Custom source path
"""

from __future__ import annotations

import json
import sys
import uuid
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

DEFAULT_SOURCE = Path(__file__).resolve().parent.parent / "Mark-XXXIX-main" / "memory" / "long_term.json"
CHROMA_HOST = "localhost"
CHROMA_PORT = 8000
SQLITE_DB = Path(__file__).resolve().parent.parent / "memory" / "sqlite" / "jarvis.db"


# ---------------------------------------------------------------------------
# Load Mark XXXIX memory
# ---------------------------------------------------------------------------

def load_mark39_memory(source: Path) -> dict:
    """Load the Mark XXXIX JSON memory file."""
    if not source.exists():
        print(f"[Migration] Source not found: {source}")
        return {}
    try:
        data = json.loads(source.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception as e:
        print(f"[Migration] Error loading {source}: {e}")
        return {}


def flatten_memory(memory: dict) -> list[dict]:
    """Flatten nested memory structure into individual entries."""
    entries = []
    for category, items in memory.items():
        if not isinstance(items, dict):
            continue
        for key, entry in items.items():
            if isinstance(entry, dict) and "value" in entry:
                entries.append({
                    "id": f"mark39_{category}_{key}",
                    "category": category,
                    "key": key,
                    "value": entry["value"],
                    "updated": entry.get("updated", ""),
                    "source": "mark39_migration",
                })
            elif isinstance(entry, str):
                entries.append({
                    "id": f"mark39_{category}_{key}",
                    "category": category,
                    "key": key,
                    "value": entry,
                    "updated": "",
                    "source": "mark39_migration",
                })
    return entries


# ---------------------------------------------------------------------------
# Migrate to Chroma
# ---------------------------------------------------------------------------

def migrate_to_chroma(entries: list[dict], execute: bool = False) -> int:
    """Migrate entries to Chroma vector database."""
    if not entries:
        print("[Migration] No entries to migrate to Chroma")
        return 0

    if not execute:
        print(f"[Migration] Would migrate {len(entries)} entries to Chroma")
        return len(entries)

    try:
        import chromadb
        client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
        collection = client.get_or_create_collection(
            "sage_episodic",
            metadata={"description": "Migrated from Mark XXXIX JSON memory"}
        )

        count = 0
        for entry in entries:
            doc_text = f"{entry['category']}/{entry['key']}: {entry['value']}"
            collection.add(
                documents=[doc_text],
                metadatas=[{
                    "category": entry["category"],
                    "key": entry["key"],
                    "source": entry["source"],
                    "updated": entry["updated"],
                }],
                ids=[entry["id"]],
            )
            count += 1
            if count % 10 == 0:
                print(f"[Migration] Chroma: {count}/{len(entries)} entries")

        print(f"[Migration] Chroma: migrated {count} entries")
        return count

    except Exception as e:
        print(f"[Migration] Chroma error: {e}")
        return 0


# ---------------------------------------------------------------------------
# Migrate to SQLite
# ---------------------------------------------------------------------------

def migrate_to_sqlite(entries: list[dict], execute: bool = False) -> int:
    """Migrate entries to SQLite memory store."""
    if not entries:
        print("[Migration] No entries to migrate to SQLite")
        return 0

    if not execute:
        print(f"[Migration] Would migrate {len(entries)} entries to SQLite")
        return len(entries)

    try:
        import sqlite3
        SQLITE_DB.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(SQLITE_DB))

        conn.execute("""
            CREATE TABLE IF NOT EXISTS memory_entries (
                id TEXT PRIMARY KEY,
                category TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                updated TEXT,
                source TEXT DEFAULT 'mark39_migration',
                migrated_at TEXT NOT NULL
            )
        """)

        now = datetime.now().isoformat()
        count = 0
        for entry in entries:
            conn.execute(
                """INSERT OR REPLACE INTO memory_entries
                   (id, category, key, value, updated, source, migrated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (entry["id"], entry["category"], entry["key"],
                 entry["value"], entry["updated"], entry["source"], now),
            )
            count += 1

        conn.commit()
        conn.close()
        print(f"[Migration] SQLite: migrated {count} entries to {SQLITE_DB}")
        return count

    except Exception as e:
        print(f"[Migration] SQLite error: {e}")
        return 0


# ---------------------------------------------------------------------------
# Archive original
# ---------------------------------------------------------------------------

def archive_original(source: Path, execute: bool = False):
    """Archive the original Mark XXXIX memory file."""
    if not source.exists():
        return

    archive_path = source.parent / f"long_term.json.mark39_archive_{datetime.now().strftime('%Y%m%dT%H%M%S')}"

    if not execute:
        print(f"[Migration] Would archive {source} -> {archive_path.name}")
        return

    source.rename(archive_path)
    print(f"[Migration] Archived: {archive_path.name}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Migrate Mark XXXIX memory to SAGE")
    parser.add_argument("--execute", action="store_true", help="Actually perform migration")
    parser.add_argument("--source", type=str, default=str(DEFAULT_SOURCE), help="Source JSON path")
    args = parser.parse_args()

    source = Path(args.source)
    execute = args.execute

    print(f"[Migration] Source: {source}")
    print(f"[Migration] Mode: {'EXECUTE' if execute else 'DRY RUN'}")
    print()

    # Load
    memory = load_mark39_memory(source)
    if not memory:
        print("[Migration] No memory data found. Nothing to migrate.")
        return

    # Flatten
    entries = flatten_memory(memory)
    print(f"[Migration] Found {len(entries)} entries across {len(memory)} categories")
    for cat, items in memory.items():
        count = len(items) if isinstance(items, dict) else 0
        print(f"  {cat}: {count} entries")
    print()

    # Migrate
    chroma_count = migrate_to_chroma(entries, execute)
    sqlite_count = migrate_to_sqlite(entries, execute)

    # Archive
    if execute:
        archive_original(source, execute)

    # Summary
    print()
    print(f"[Migration] Summary:")
    print(f"  Entries: {len(entries)}")
    print(f"  Chroma:  {chroma_count} migrated")
    print(f"  SQLite:  {sqlite_count} migrated")
    if execute:
        print(f"  Original archived")


if __name__ == "__main__":
    main()
