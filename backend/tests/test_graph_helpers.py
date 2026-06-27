from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.config import Settings
from app.db import QueryRepository
from app.graph import QuorumCouncil
from app.schemas import ContradictionCard, EvidenceCard


class CouncilHelperTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        root = Path(self.temp_dir.name)
        settings = Settings(
            sqlite_path=str(root / "quorum.db"),
            chroma_path=str(root / "chroma"),
            enable_demo_mode=True,
        )
        repo = QueryRepository(settings.sqlite_file)
        repo.init()
        self.council = QuorumCouncil(settings, repo)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_confidence_score_rises_on_second_pass(self) -> None:
        evidence = [
            EvidenceCard(
                source_id="1",
                source_title="Paper 1",
                provider="semantic_scholar",
                claim="Claim",
                methodology="Systematic review or meta-analysis",
                findings="Finding",
                limitations=["Limit"],
                stance="supports",
                evidence_strength="high",
                highlight="Highlight",
            )
        ]
        contradictions = [
            ContradictionCard(
                summary="Some disagreement",
                explanation="Details",
                severity="medium",
                source_ids=["1"],
            )
        ]
        first_pass = self.council._confidence_score(
            evidence_cards=evidence,
            contradiction_cards=contradictions,
            pass_index=1,
            simulated=False,
        )
        second_pass = self.council._confidence_score(
            evidence_cards=evidence,
            contradiction_cards=contradictions,
            pass_index=2,
            simulated=False,
        )
        self.assertGreater(second_pass, first_pass)

    def test_fallback_plan_contains_multiple_queries(self) -> None:
        plan = self.council._fallback_plan("Does RAG reduce hallucinations?", 1, [])
        self.assertGreaterEqual(len(plan["search_queries"]), 3)


if __name__ == "__main__":
    unittest.main()

