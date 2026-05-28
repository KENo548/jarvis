import tempfile
import unittest
from pathlib import Path

import sys


ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import memory_store
import researcher


class Phase2MemoryTests(unittest.TestCase):
    def test_store_and_search_notes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "jarvis.db"
            memory_store.store_note(
                title="Chroma setup",
                content="Install local vector memory and wire the researcher agent.",
                source_type="doc",
                source_ref="docs/ROADMAP.md#phase2",
                tags=["phase2", "memory"],
                db_path=db_path,
            )

            results = memory_store.search_notes("researcher memory", db_path=db_path)

            self.assertEqual(len(results), 1)
            self.assertEqual(results[0].title, "Chroma setup")

    def test_researcher_capture_exports_to_obsidian(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "jarvis.db"
            vault_path = Path(temp_dir) / "vault"
            note = researcher.capture_finding(
                title="Search integration",
                content="Add browser-mcp and search-mcp to support research workflows.",
                source_ref="docs/ROADMAP.md#phase2",
                tags=["research", "search"],
                confidence=0.9,
                db_path=db_path,
                vault_path=vault_path,
            )

            self.assertEqual(note["title"], "Search integration")
            self.assertIn("obsidian_path", note)
            self.assertTrue(Path(note["obsidian_path"]).exists())


if __name__ == "__main__":
    unittest.main()