import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import embedding_client


class EmbeddingBackendTests(unittest.TestCase):
    def test_deterministic_embedding_shape(self):
        vec = embedding_client.embed_text("hello world this is a test", provider="deterministic")
        self.assertIsInstance(vec, list)
        self.assertEqual(len(vec), embedding_client.NOMIC_EMBED_DIMS)

    def test_deterministic_embedding_deterministic(self):
        v1 = embedding_client.embed_text("same input", provider="deterministic")
        v2 = embedding_client.embed_text("same input", provider="deterministic")
        self.assertEqual(v1, v2)

    def test_deterministic_embedding_empty(self):
        vec = embedding_client.embed_text("", provider="deterministic")
        self.assertEqual(len(vec), embedding_client.NOMIC_EMBED_DIMS)
        self.assertTrue(all(v == 0.0 for v in vec))

    def test_backend_probe_returns_valid(self):
        backend = embedding_client.embedding_backend()
        self.assertIn(backend, ("ollama-nomic-embed-text", "deterministic"))

    def test_embedding_dim(self):
        dim = embedding_client.embedding_dim()
        self.assertEqual(dim, 768)

    def test_ollama_provider_works_or_raises(self):
        """Ollama provider returns real embeddings or raises when unreachable."""
        try:
            vec = embedding_client.embed_text("test", provider="ollama")
            # Ollama is running — verify real embedding
            self.assertIsInstance(vec, list)
            self.assertEqual(len(vec), 768)
        except (ConnectionError, OSError, ValueError):
            pass  # Expected when Ollama is not running

    def test_auto_provider_falls_back(self):
        vec = embedding_client.embed_text("test", provider="auto")
        self.assertIsInstance(vec, list)
        self.assertEqual(len(vec), 768)

    def test_nomic_model_constant(self):
        self.assertEqual(embedding_client.NOMIC_EMBED_MODEL, "nomic-embed-text")
        self.assertEqual(embedding_client.NOMIC_EMBED_DIMS, 768)


if __name__ == "__main__":
    unittest.main()
