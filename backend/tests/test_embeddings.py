from __future__ import annotations

import math
import unittest

from app.utils.embeddings import embed_text


class EmbeddingTests(unittest.TestCase):
    def test_embedding_is_deterministic(self) -> None:
        first = embed_text("agentic research systems")
        second = embed_text("agentic research systems")
        self.assertEqual(first, second)

    def test_embedding_is_normalized(self) -> None:
        vector = embed_text("quorum confidence retry loop")
        norm = math.sqrt(sum(value * value for value in vector))
        self.assertAlmostEqual(norm, 1.0, places=5)


if __name__ == "__main__":
    unittest.main()

