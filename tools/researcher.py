#!/usr/bin/env python3
"""Research capture and retrieval for JARVIS."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import memory_store
import research_gateway


def capture_finding(
    title: str,
    content: str,
    source_ref: str,
    tags: list[str] | None = None,
    confidence: float = 0.5,
    db_path: Path | None = None,
    vault_path: Path | None = None,
) -> dict[str, object]:
    note = memory_store.store_note(
        title=title,
        content=content,
        source_type="research",
        source_ref=source_ref,
        tags=tags or [],
        confidence=confidence,
        db_path=db_path or memory_store.DB_PATH,
    )
    obsidian_path = memory_store.export_to_obsidian(note, vault_path=vault_path or memory_store.OBSIDIAN_VAULT)
    return {
        "note_id": note.note_id,
        "title": note.title,
        "source_ref": note.source_ref,
        "obsidian_path": str(obsidian_path),
        "tags": note.tags,
        "confidence": note.confidence,
    }


def research_topic(
    query: str,
    searxng_url: str = "http://localhost:8888",
    limit: int = 5,
    db_path: Path | None = None,
    vault_path: Path | None = None,
) -> dict[str, object]:
    hits = research_gateway.search_web(query, searxng_url=searxng_url, limit=limit)
    stored_notes: list[dict[str, object]] = []
    for hit in hits:
        page = research_gateway.capture_page(hit.url)
        stored = capture_finding(
            title=page.title,
            content=page.text,
            source_ref=hit.url,
            tags=["research", "search"],
            confidence=0.7,
            db_path=db_path,
            vault_path=vault_path,
        )
        stored_notes.append(stored)

    summary_note = memory_store.store_note(
        title=f"Research summary: {query}",
        content=json.dumps(
            {
                "query": query,
                "results": [
                    {"title": hit.title, "url": hit.url, "snippet": hit.snippet}
                    for hit in hits
                ],
            },
            indent=2,
            sort_keys=True,
        ),
        source_type="research-summary",
        source_ref=f"search:{query}",
        tags=["research", "summary"],
        confidence=0.8,
        db_path=db_path or memory_store.DB_PATH,
    )
    memory_store.export_to_obsidian(summary_note, vault_path=vault_path or memory_store.OBSIDIAN_VAULT)

    return {
        "query": query,
        "results": [
            {"title": hit.title, "url": hit.url, "snippet": hit.snippet}
            for hit in hits
        ],
        "stored_notes": stored_notes,
        "summary_note_id": summary_note.note_id,
    }


def search_findings(query: str, limit: int = 10) -> list[dict[str, object]]:
    notes = memory_store.search_notes(query, limit=limit)
    return [
        {
            "note_id": note.note_id,
            "title": note.title,
            "source_ref": note.source_ref,
            "tags": note.tags,
            "confidence": note.confidence,
            "content": note.content,
        }
        for note in notes
    ]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="JARVIS researcher")
    subparsers = parser.add_subparsers(dest="command", required=True)

    capture_parser = subparsers.add_parser("capture", help="Capture a research finding")
    capture_parser.add_argument("title")
    capture_parser.add_argument("content")
    capture_parser.add_argument("source_ref")
    capture_parser.add_argument("--tags", nargs="*", default=[])
    capture_parser.add_argument("--confidence", type=float, default=0.5)

    search_parser = subparsers.add_parser("search", help="Search captured findings")
    search_parser.add_argument("query")
    search_parser.add_argument("--limit", type=int, default=10)

    research_parser = subparsers.add_parser("research", help="Search the web and store captured findings")
    research_parser.add_argument("query")
    research_parser.add_argument("--searxng-url", default="http://localhost:8888")
    research_parser.add_argument("--limit", type=int, default=5)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "capture":
        result = capture_finding(
            title=args.title,
            content=args.content,
            source_ref=args.source_ref,
            tags=args.tags,
            confidence=args.confidence,
        )
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0

    if args.command == "search":
        result = search_findings(args.query, limit=args.limit)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0

    if args.command == "research":
        result = research_topic(args.query, searxng_url=args.searxng_url, limit=args.limit)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())