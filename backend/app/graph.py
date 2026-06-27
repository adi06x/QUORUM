from __future__ import annotations

import asyncio
import logging
import math
from typing import Any, Literal, TypedDict

from langgraph.graph import END, START, StateGraph

from app.config import Settings
from app.db import QueryRepository
from app.schemas import (
    ContradictionCard,
    EvidenceCard,
    InvestigationStep,
    QueryRequest,
    SourceRecord,
    TimelineEvent,
    VerdictPayload,
)
from app.services.llm import JsonLlmClient
from app.services.research import ResearchRetriever
from app.services.vector_store import EvidenceVectorStore

logger = logging.getLogger(__name__)

_CRITICAL_GAP_MARKERS = {"no evidence", "absent", "unknown", "unresolved", "no data", "lack of"}


class CouncilState(TypedDict, total=False):
    query_id: str
    question: str
    pass_count: int
    max_passes: int
    confidence_threshold: float
    mode: str
    simulated_research: bool
    investigation_plan: list[dict[str, Any]]
    sources: list[dict[str, Any]]
    evidence_cards: list[dict[str, Any]]
    contradiction_cards: list[dict[str, Any]]
    verdict: str
    council_summary: str
    supporting_evidence: list[str]
    limitations: list[str]
    recommended_next_steps: list[str]
    confidence_score: float
    provider_notes: list[str]
    # Gap-Finder fields
    research_gaps: list[str]
    gap_summary: str
    has_critical_gaps: bool
    # Archivist fields
    formatted_citations: list[str]
    previous_related_queries: list[str]


class QuorumCouncil:
    def __init__(self, settings: Settings, repo: QueryRepository) -> None:
        self.settings = settings
        self.repo = repo
        self.llm = JsonLlmClient(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            model=settings.llm_model,
            timeout_seconds=settings.llm_timeout_seconds,
        )
        self.retriever = ResearchRetriever(
            semantic_scholar_api_key=settings.semantic_scholar_api_key,
            max_sources_per_provider=settings.max_sources_per_provider,
            enable_demo_mode=settings.enable_demo_mode,
        )
        self.vector_store = EvidenceVectorStore(str(settings.chroma_dir))
        self.graph = self._build_graph()

    async def run_query(self, query_id: str, request: QueryRequest) -> None:
        initial_state: CouncilState = {
            "query_id": query_id,
            "question": request.question.strip(),
            "pass_count": 0,
            "max_passes": request.max_passes or self.settings.max_research_passes,
            "confidence_threshold": request.confidence_threshold or self.settings.default_confidence_threshold,
            "investigation_plan": [],
            "sources": [],
            "evidence_cards": [],
            "contradiction_cards": [],
            "provider_notes": [],
            "research_gaps": [],
            "gap_summary": "",
            "has_critical_gaps": False,
            "formatted_citations": [],
            "previous_related_queries": [],
        }

        try:
            self.repo.update_query(
                query_id,
                status="running",
                current_stage="planning",
                current_message="Chair agent is decomposing the research question.",
            )
            final_state = await self.graph.ainvoke(initial_state)
            result = VerdictPayload(
                final_verdict=final_state.get("verdict", "The council could not reach a verdict."),
                confidence_score=float(final_state.get("confidence_score", 0.0)),
                supporting_evidence=final_state.get("supporting_evidence", []),
                contradictions=[item["summary"] for item in final_state.get("contradiction_cards", [])],
                limitations=final_state.get("limitations", []),
                recommended_next_steps=final_state.get("recommended_next_steps", []),
                sources=[SourceRecord.model_validate(item) for item in final_state.get("sources", [])],
                evidence_cards=[EvidenceCard.model_validate(item) for item in final_state.get("evidence_cards", [])],
                contradiction_cards=[
                    ContradictionCard.model_validate(item) for item in final_state.get("contradiction_cards", [])
                ],
                mode=final_state.get("mode", "live"),
                simulated_research=bool(final_state.get("simulated_research", False)),
                council_summary=final_state.get("council_summary", ""),
                passes_completed=int(final_state.get("pass_count", 1)),
                research_gaps=final_state.get("research_gaps", []),
                gap_summary=final_state.get("gap_summary", ""),
                has_critical_gaps=bool(final_state.get("has_critical_gaps", False)),
                formatted_citations=final_state.get("formatted_citations", []),
                previous_related_queries=final_state.get("previous_related_queries", []),
            )
            self.repo.update_query(
                query_id,
                status="completed",
                current_stage="completed",
                current_message="Council delivered the final verdict.",
                pass_count=int(final_state.get("pass_count", 1)),
                confidence_score=result.confidence_score,
                mode=result.mode,
                simulated_research=result.simulated_research,
                state_patch=self._state_patch(final_state),
                result=result.model_dump(mode="json"),
                append_timeline=[
                    self._event(
                        agent="System",
                        stage="system",
                        status="complete",
                        title="Council adjourned",
                        detail="QUORUM finalized the verdict package and archived the working notes.",
                        pass_index=int(final_state.get("pass_count", 1)),
                    )
                ],
            )
        except Exception as exc:
            logger.error("run_query: unrecoverable error for query %s: %s", query_id, exc, exc_info=True)
            self.repo.update_query(
                query_id,
                status="failed",
                current_stage="error",
                current_message="The council encountered an unrecoverable error.",
                error_message=str(exc),
                append_timeline=[
                    self._event(
                        agent="System",
                        stage="system",
                        status="error",
                        title="Council interrupted",
                        detail=str(exc),
                        pass_index=initial_state["pass_count"] or 1,
                    )
                ],
            )

    def _build_graph(self):
        builder = StateGraph(CouncilState)
        builder.add_node("chair", self.chair_agent)
        builder.add_node("scout", self.scout_agent)
        builder.add_node("reader", self.reader_agent)
        builder.add_node("critic", self.critic_agent)
        builder.add_node("synthesizer", self.synthesizer_agent)
        builder.add_node("gap_finder", self.gap_finder_agent)
        builder.add_node("archivist", self.archivist_agent)
        builder.add_node("retry", self.retry_agent)
        builder.add_edge(START, "chair")
        builder.add_edge("chair", "scout")
        builder.add_edge("scout", "reader")
        builder.add_edge("reader", "critic")
        builder.add_edge("critic", "synthesizer")
        builder.add_edge("synthesizer", "gap_finder")
        builder.add_edge("gap_finder", "archivist")
        builder.add_conditional_edges("archivist", self._decide_next_step, {"retry": "retry", "done": END})
        builder.add_edge("retry", "chair")
        return builder.compile()

    # ── Chair Agent ────────────────────────────────────────────────────────────

    async def chair_agent(self, state: CouncilState) -> CouncilState:
        logger.info("chair_agent: starting pass %d", int(state.get("pass_count", 0)) + 1)
        pass_index = int(state.get("pass_count", 0)) + 1
        previous_contradictions = [item.get("summary", "") for item in state.get("contradiction_cards", [])]
        previous_limitations = state.get("limitations", [])
        fallback = self._fallback_plan(state["question"], pass_index, previous_contradictions)
        try:
            response = await self.llm.generate_json(
                system_prompt=(
                    "You are the Chair Agent for QUORUM, an AI research council. Break the user's research question into "
                    "a concise investigation brief. Return JSON with keys council_brief, sub_questions, search_queries, "
                    "and success_criteria. Each search query should be specific and academic."
                ),
                user_payload={
                    "question": state["question"],
                    "pass_index": pass_index,
                    "previous_contradictions": previous_contradictions,
                    "previous_limitations": previous_limitations,
                    "available_sources": len(state.get("sources", [])),
                },
                fallback=fallback,
            )
        except Exception as exc:
            logger.warning("chair_agent: LLM call failed, using fallback. Error: %s", exc)
            response = fallback

        investigation_plan = [
            InvestigationStep(
                focus=sub_question,
                key_questions=response.get("success_criteria", [])[:2],
                search_query=response.get("search_queries", [state["question"]])[index]
                if index < len(response.get("search_queries", []))
                else state["question"],
            ).model_dump(mode="json")
            for index, sub_question in enumerate(response.get("sub_questions", fallback["sub_questions"])[:3])
        ]
        detail = response.get("council_brief", fallback["council_brief"])
        self.repo.update_query(
            state["query_id"],
            status="running",
            current_stage="planning",
            current_message=f"Chair completed planning pass {pass_index}.",
            pass_count=pass_index,
            append_timeline=[
                self._event(
                    agent="Chair",
                    stage="planning",
                    status="complete",
                    title=f"Chair drafted investigation plan for pass {pass_index}",
                    detail=detail,
                    pass_index=pass_index,
                )
            ],
            state_patch={"investigation_plan": investigation_plan},
        )
        logger.info("chair_agent: completed pass %d", pass_index)
        return {
            "pass_count": pass_index,
            "investigation_plan": investigation_plan,
        }

    # ── Scout Agent ────────────────────────────────────────────────────────────

    async def scout_agent(self, state: CouncilState) -> CouncilState:
        pass_index = int(state.get("pass_count", 1))
        logger.info("scout_agent: starting pass %d", pass_index)
        self.repo.update_query(
            state["query_id"],
            status="running",
            current_stage="retrieval",
            current_message=f"Scout is retrieving papers for pass {pass_index}.",
        )
        plan = [InvestigationStep.model_validate(item) for item in state.get("investigation_plan", [])]
        sources, mode, simulated_research, provider_notes = await self.retriever.gather_sources(
            state["question"],
            plan,
            pass_index,
        )
        self.vector_store.upsert_sources(state["query_id"], sources)
        if sources:
            related = self.vector_store.query_related(
                state["query_id"],
                state["question"],
                limit=min(6, len(sources)),
            )
            if related:
                ranked_ids = [item["id"] for item in related]
                source_map = {source.id: source for source in sources}
                ordered_sources = [source_map[source_id] for source_id in ranked_ids if source_id in source_map]
                trailing_sources = [source for source in sources if source.id not in ranked_ids]
                sources = ordered_sources + trailing_sources

        note_text = " ".join(provider_notes).strip()
        detail = (
            f"Collected {len(sources)} sources from Semantic Scholar, arXiv, and CrossRef."
            if not simulated_research
            else "Live APIs were unavailable, so Scout switched to clearly labeled simulated academic results."
        )
        if note_text:
            detail = f"{detail} {note_text}"
        self.repo.update_query(
            state["query_id"],
            status="running",
            current_stage="retrieval",
            current_message=f"Scout curated {len(sources)} sources for pass {pass_index}.",
            mode=mode,
            simulated_research=simulated_research,
            append_timeline=[
                self._event(
                    agent="Scout",
                    stage="retrieval",
                    status="complete",
                    title=f"Scout assembled the source docket for pass {pass_index}",
                    detail=detail,
                    pass_index=pass_index,
                )
            ],
            state_patch={
                "sources": [source.model_dump(mode="json") for source in sources],
                "provider_notes": provider_notes,
            },
        )
        logger.info("scout_agent: completed with %d sources", len(sources))
        return {
            "sources": [source.model_dump(mode="json") for source in sources],
            "mode": mode,
            "simulated_research": simulated_research,
            "provider_notes": provider_notes,
        }

    # ── Reader Agent ───────────────────────────────────────────────────────────

    async def reader_agent(self, state: CouncilState) -> CouncilState:
        pass_index = int(state.get("pass_count", 1))
        logger.info("reader_agent: starting pass %d", pass_index)
        self.repo.update_query(
            state["query_id"],
            status="running",
            current_stage="reading",
            current_message=f"Reader is extracting claims and methods for pass {pass_index}.",
        )
        sources = [SourceRecord.model_validate(item) for item in state.get("sources", [])][:6]
        fallback_cards = [self._fallback_evidence_card(source).model_dump(mode="json") for source in sources]
        try:
            response = await self.llm.generate_json(
                system_prompt=(
                    "You are the Reader Agent for QUORUM. Review the provided sources and extract structured research notes. "
                    "Return JSON with a top-level key evidence_cards. Each card must include source_id, claim, methodology, "
                    "findings, limitations, stance, evidence_strength, and highlight."
                ),
                user_payload={
                    "question": state["question"],
                    "sources": [source.model_dump(mode="json") for source in sources],
                },
                fallback={"evidence_cards": fallback_cards},
                temperature=0.15,
            )
        except Exception as exc:
            logger.warning("reader_agent: LLM call failed, using fallback. Error: %s", exc)
            response = {"evidence_cards": fallback_cards}

        evidence_cards: list[dict[str, Any]] = []
        for source in sources:
            matched = next(
                (item for item in response.get("evidence_cards", []) if item.get("source_id") == source.id),
                None,
            )
            if matched is None:
                evidence_cards.append(self._fallback_evidence_card(source).model_dump(mode="json"))
                continue
            evidence_cards.append(
                EvidenceCard(
                    source_id=source.id,
                    source_title=source.title,
                    provider=source.provider,
                    claim=matched.get("claim", source.title),
                    methodology=matched.get("methodology", "Methodology not specified in the abstract."),
                    findings=matched.get("findings", source.abstract[:240]),
                    limitations=matched.get("limitations", []),
                    stance=matched.get("stance", "neutral"),
                    evidence_strength=matched.get("evidence_strength", "preliminary"),
                    highlight=matched.get("highlight", source.abstract[:180]),
                ).model_dump(mode="json")
            )
        self.repo.update_query(
            state["query_id"],
            status="running",
            current_stage="reading",
            current_message=f"Reader distilled {len(evidence_cards)} evidence cards.",
            append_timeline=[
                self._event(
                    agent="Reader",
                    stage="reading",
                    status="complete",
                    title=f"Reader extracted structured evidence for pass {pass_index}",
                    detail=f"Reader summarized claims, methodology, findings, and limitations from {len(evidence_cards)} sources.",
                    pass_index=pass_index,
                )
            ],
            state_patch={"evidence_cards": evidence_cards},
        )
        logger.info("reader_agent: extracted %d evidence cards", len(evidence_cards))
        return {"evidence_cards": evidence_cards}

    # ── Critic Agent ───────────────────────────────────────────────────────────

    async def critic_agent(self, state: CouncilState) -> CouncilState:
        pass_index = int(state.get("pass_count", 1))
        logger.info("critic_agent: starting pass %d", pass_index)
        self.repo.update_query(
            state["query_id"],
            status="running",
            current_stage="critique",
            current_message=f"Critic is challenging the evidence for pass {pass_index}.",
        )
        evidence_cards = [EvidenceCard.model_validate(item) for item in state.get("evidence_cards", [])]
        fallback = self._fallback_critique(evidence_cards, bool(state.get("simulated_research", False)))
        try:
            response = await self.llm.generate_json(
                system_prompt=(
                    "You are the Critic Agent for QUORUM. Challenge the evidence and identify contradictions, weak signals, "
                    "and missing information. Return JSON with contradiction_cards, limitations, and debate_summary."
                ),
                user_payload={
                    "question": state["question"],
                    "evidence_cards": [card.model_dump(mode="json") for card in evidence_cards],
                    "simulated_research": state.get("simulated_research", False),
                },
                fallback=fallback,
                temperature=0.25,
            )
        except Exception as exc:
            logger.warning("critic_agent: LLM call failed, using fallback. Error: %s", exc)
            response = fallback

        contradiction_cards = [
            ContradictionCard(
                summary=item.get("summary", "Evidence tension identified."),
                explanation=item.get("explanation", "The council found meaningful disagreement across sources."),
                severity=item.get("severity", "medium"),
                source_ids=item.get("source_ids", []),
            ).model_dump(mode="json")
            for item in response.get("contradiction_cards", fallback["contradiction_cards"])
        ]
        limitations = list(dict.fromkeys(response.get("limitations", fallback["limitations"])))
        debate_summary = response.get("debate_summary", fallback["debate_summary"])
        self.repo.update_query(
            state["query_id"],
            status="running",
            current_stage="critique",
            current_message=f"Critic surfaced {len(contradiction_cards)} contradictions and gaps.",
            append_timeline=[
                self._event(
                    agent="Critic",
                    stage="critique",
                    status="complete",
                    title=f"Critic stress-tested the evidence for pass {pass_index}",
                    detail=debate_summary,
                    pass_index=pass_index,
                )
            ],
            state_patch={"contradiction_cards": contradiction_cards},
        )
        logger.info("critic_agent: found %d contradictions", len(contradiction_cards))
        return {"contradiction_cards": contradiction_cards, "limitations": limitations}

    # ── Synthesizer Agent ──────────────────────────────────────────────────────

    async def synthesizer_agent(self, state: CouncilState) -> CouncilState:
        pass_index = int(state.get("pass_count", 1))
        logger.info("synthesizer_agent: starting pass %d", pass_index)
        self.repo.update_query(
            state["query_id"],
            status="running",
            current_stage="synthesis",
            current_message=f"Synthesizer is drafting the verdict for pass {pass_index}.",
        )
        evidence_cards = [EvidenceCard.model_validate(item) for item in state.get("evidence_cards", [])]
        contradiction_cards = [ContradictionCard.model_validate(item) for item in state.get("contradiction_cards", [])]
        heuristic_score = self._confidence_score(
            evidence_cards=evidence_cards,
            contradiction_cards=contradiction_cards,
            pass_index=pass_index,
            simulated=bool(state.get("simulated_research", False)),
        )
        fallback = self._fallback_synthesis(
            state["question"],
            evidence_cards,
            contradiction_cards,
            heuristic_score,
            pass_index,
        )
        try:
            response = await self.llm.generate_json(
                system_prompt=(
                    "You are the Synthesizer Agent for QUORUM. Deliver a committee-style verdict. Return JSON with keys "
                    "final_verdict, confidence_score, supporting_evidence, recommended_next_steps, council_summary, and limitations."
                ),
                user_payload={
                    "question": state["question"],
                    "confidence_threshold": state["confidence_threshold"],
                    "pass_index": pass_index,
                    "evidence_cards": [card.model_dump(mode="json") for card in evidence_cards],
                    "contradiction_cards": [card.model_dump(mode="json") for card in contradiction_cards],
                    "limitations": state.get("limitations", []),
                    "provider_notes": state.get("provider_notes", []),
                },
                fallback=fallback,
                temperature=0.2,
            )
        except Exception as exc:
            logger.warning("synthesizer_agent: LLM call failed, using fallback. Error: %s", exc)
            response = fallback

        confidence_score = float(response.get("confidence_score", heuristic_score))
        confidence_score = max(0.35, min(confidence_score, 0.95))
        supporting_evidence = response.get("supporting_evidence", fallback["supporting_evidence"])[:4]
        recommended_next_steps = response.get("recommended_next_steps", fallback["recommended_next_steps"])[:4]
        limitations = list(dict.fromkeys(response.get("limitations", fallback["limitations"])))
        verdict = response.get("final_verdict", fallback["final_verdict"])
        council_summary = response.get("council_summary", fallback["council_summary"])
        detail = f"Synthesizer produced a {confidence_score:.0%} confidence verdict on pass {pass_index}."
        self.repo.update_query(
            state["query_id"],
            status="running",
            current_stage="synthesis",
            current_message=detail,
            confidence_score=confidence_score,
            append_timeline=[
                self._event(
                    agent="Synthesizer",
                    stage="synthesis",
                    status="complete",
                    title=f"Synthesizer delivered a committee verdict for pass {pass_index}",
                    detail=detail,
                    pass_index=pass_index,
                )
            ],
            state_patch={
                "evidence_cards": [card.model_dump(mode="json") for card in evidence_cards],
                "contradiction_cards": [card.model_dump(mode="json") for card in contradiction_cards],
            },
        )
        logger.info("synthesizer_agent: confidence=%.2f", confidence_score)
        return {
            "verdict": verdict,
            "supporting_evidence": supporting_evidence,
            "recommended_next_steps": recommended_next_steps,
            "limitations": limitations,
            "council_summary": council_summary,
            "confidence_score": confidence_score,
        }

    # ── Gap-Finder Agent ───────────────────────────────────────────────────────

    async def gap_finder_agent(self, state: CouncilState) -> CouncilState:
        pass_index = int(state.get("pass_count", 1))
        logger.info("gap_finder_agent: starting pass %d", pass_index)
        self.repo.update_query(
            state["query_id"],
            status="running",
            current_stage="synthesis",
            current_message=f"Gap-Finder is identifying research gaps for pass {pass_index}.",
        )
        evidence_cards = [EvidenceCard.model_validate(item) for item in state.get("evidence_cards", [])]
        contradiction_cards = [ContradictionCard.model_validate(item) for item in state.get("contradiction_cards", [])]
        limitations = state.get("limitations", [])
        recommended_next_steps = state.get("recommended_next_steps", [])
        fallback = self._fallback_gap_finder(evidence_cards, contradiction_cards, limitations)

        try:
            response = await self.llm.generate_json(
                system_prompt=(
                    "You are the Gap-Finder Agent for QUORUM. Your role is to identify what is unanswered, "
                    "weak, or conflicting in the current evidence base. "
                    "Return JSON with exactly two keys: research_gaps (a list of 3–5 specific, meaningful "
                    "research gaps — not generic statements) and gap_summary (a single paragraph summarizing "
                    "the overall state of the evidence gaps)."
                ),
                user_payload={
                    "question": state["question"],
                    "evidence_cards": [card.model_dump(mode="json") for card in evidence_cards],
                    "contradiction_cards": [card.model_dump(mode="json") for card in contradiction_cards],
                    "limitations": limitations,
                    "recommended_next_steps": recommended_next_steps,
                },
                fallback=fallback,
                temperature=0.2,
            )
        except Exception as exc:
            logger.warning("gap_finder_agent: LLM call failed, using fallback. Error: %s", exc)
            response = fallback

        research_gaps: list[str] = response.get("research_gaps", fallback["research_gaps"])[:5]
        gap_summary: str = response.get("gap_summary", fallback["gap_summary"])

        # Detect critical gaps
        combined_gap_text = " ".join(research_gaps).lower()
        has_critical_gaps = any(marker in combined_gap_text for marker in _CRITICAL_GAP_MARKERS)

        self.repo.update_query(
            state["query_id"],
            status="running",
            current_stage="synthesis",
            current_message=f"Gap-Finder identified {len(research_gaps)} research gaps.",
            append_timeline=[
                self._event(
                    agent="Gap-Finder",
                    stage="synthesis",
                    status="complete",
                    title=f"Gap-Finder surfaced {len(research_gaps)} specific research gaps",
                    detail=gap_summary,
                    pass_index=pass_index,
                )
            ],
            state_patch={
                "research_gaps": research_gaps,
                "gap_summary": gap_summary,
                "has_critical_gaps": has_critical_gaps,
            },
        )
        logger.info("gap_finder_agent: found %d gaps, critical=%s", len(research_gaps), has_critical_gaps)
        return {
            "research_gaps": research_gaps,
            "gap_summary": gap_summary,
            "has_critical_gaps": has_critical_gaps,
        }

    # ── Archivist Agent ────────────────────────────────────────────────────────

    async def archivist_agent(self, state: CouncilState) -> CouncilState:
        pass_index = int(state.get("pass_count", 1))
        logger.info("archivist_agent: starting pass %d", pass_index)
        self.repo.update_query(
            state["query_id"],
            status="running",
            current_stage="system",
            current_message=f"Archivist is formatting citations and archiving the session.",
        )
        sources = [SourceRecord.model_validate(item) for item in state.get("sources", [])]
        fallback = self._fallback_archivist(sources)

        # Query ChromaDB for similar past research (across other query collections)
        previous_related_queries: list[str] = []
        try:
            # We query from all collections using the global query. The vector store
            # only has one collection per query_id, so we use the current one.
            related_items = self.vector_store.query_related(
                state["query_id"],
                state["question"],
                limit=3,
            )
            # Extract question-like info from metadata (titles as proxy for past queries)
            for item in related_items:
                meta = item.get("metadata", {})
                title = meta.get("title", "")
                if title and title not in previous_related_queries:
                    previous_related_queries.append(title)
        except Exception as exc:
            logger.warning("archivist_agent: vector store query failed: %s", exc)

        try:
            response = await self.llm.generate_json(
                system_prompt=(
                    "You are the Archivist Agent for QUORUM. Your role is to produce properly formatted citations "
                    "and archive the research session. Format each source as an APA-style citation string. "
                    "Return JSON with exactly two keys: formatted_citations (list of APA citation strings, "
                    "one per source) and archive_summary (a single sentence describing what was archived)."
                ),
                user_payload={
                    "question": state["question"],
                    "sources": [source.model_dump(mode="json") for source in sources],
                },
                fallback=fallback,
                temperature=0.1,
            )
        except Exception as exc:
            logger.warning("archivist_agent: LLM call failed, using fallback. Error: %s", exc)
            response = fallback

        formatted_citations: list[str] = response.get("formatted_citations", fallback["formatted_citations"])
        archive_summary: str = response.get("archive_summary", fallback["archive_summary"])

        self.repo.update_query(
            state["query_id"],
            status="running",
            current_stage="system",
            current_message=f"Archivist formatted {len(formatted_citations)} citations.",
            append_timeline=[
                self._event(
                    agent="Archivist",
                    stage="system",
                    status="complete",
                    title=f"Archivist formatted {len(formatted_citations)} APA citations",
                    detail=archive_summary,
                    pass_index=pass_index,
                )
            ],
            state_patch={
                "formatted_citations": formatted_citations,
                "previous_related_queries": previous_related_queries,
            },
        )
        logger.info("archivist_agent: formatted %d citations", len(formatted_citations))
        return {
            "formatted_citations": formatted_citations,
            "previous_related_queries": previous_related_queries,
        }

    # ── Retry Agent ────────────────────────────────────────────────────────────

    async def retry_agent(self, state: CouncilState) -> CouncilState:
        pass_index = int(state.get("pass_count", 1))
        reasons = []
        confidence = float(state.get("confidence_score", 0.0))
        threshold = float(state.get("confidence_threshold", self.settings.default_confidence_threshold))
        if confidence < threshold:
            reasons.append(f"confidence {confidence:.0%} < threshold {threshold:.0%}")
        if len(state.get("sources", [])) < 4:
            reasons.append(f"only {len(state.get('sources', []))} sources retrieved (< 4)")
        high_severity = sum(1 for c in state.get("contradiction_cards", []) if c.get("severity") == "high")
        if high_severity > 2:
            reasons.append(f"{high_severity} unresolved high-severity contradictions")
        if state.get("has_critical_gaps"):
            reasons.append("Gap-Finder flagged critical unanswered research gaps")
        all_preliminary = (
            len(state.get("evidence_cards", [])) > 0
            and all(c.get("evidence_strength") == "preliminary" for c in state.get("evidence_cards", []))
        )
        if all_preliminary:
            reasons.append("all evidence cards rated preliminary strength")

        reason_str = "; ".join(reasons) if reasons else "confidence below threshold"
        detail = f"Chair triggered retry after pass {pass_index} — reasons: {reason_str}."
        self.repo.update_query(
            state["query_id"],
            status="running",
            current_stage="retry",
            current_message="Confidence fell below threshold. Launching another research pass.",
            append_timeline=[
                self._event(
                    agent="Chair",
                    stage="retry",
                    status="retry",
                    title=f"Chair triggered an autonomous retry after pass {pass_index}",
                    detail=detail,
                    pass_index=pass_index,
                )
            ],
        )
        await asyncio.sleep(0.2)
        return {}

    # ── Decision Logic ─────────────────────────────────────────────────────────

    def _decide_next_step(self, state: CouncilState) -> Literal["retry", "done"]:
        confidence = float(state.get("confidence_score", 0.0))
        threshold = float(state.get("confidence_threshold", self.settings.default_confidence_threshold))
        pass_index = int(state.get("pass_count", 1))
        max_passes = int(state.get("max_passes", self.settings.max_research_passes))

        # Hard limit always wins
        if pass_index >= max_passes:
            return "done"

        # Retry conditions
        if confidence < threshold:
            return "retry"
        if len(state.get("sources", [])) < 4:
            return "retry"
        high_severity = sum(1 for c in state.get("contradiction_cards", []) if c.get("severity") == "high")
        if high_severity > 2:
            return "retry"
        if state.get("has_critical_gaps"):
            return "retry"
        all_preliminary = (
            len(state.get("evidence_cards", [])) > 0
            and all(c.get("evidence_strength") == "preliminary" for c in state.get("evidence_cards", []))
        )
        if all_preliminary:
            return "retry"

        return "done"

    # ── Fallback Helpers ───────────────────────────────────────────────────────

    def _fallback_plan(
        self,
        question: str,
        pass_index: int,
        previous_contradictions: list[str],
    ) -> dict[str, Any]:
        suffix = " and pressure-test the weak spots" if pass_index > 1 else ""
        return {
            "council_brief": f"Break the question into evidence search, methods review, and contradiction analysis{suffix}.",
            "sub_questions": [
                "What do the highest-signal sources claim?",
                "How strong are the methods behind those claims?",
                "Where do the sources disagree or leave uncertainty?",
            ],
            "search_queries": [
                question,
                f"{question} systematic review",
                f"{question} limitations contradictory evidence {' '.join(previous_contradictions[:1])}".strip(),
            ],
            "success_criteria": [
                "Find at least one overview or benchmark-style source.",
                "Identify contradictory or low-confidence findings.",
                "Surface practical next steps for additional research.",
            ],
        }

    def _fallback_evidence_card(self, source: SourceRecord) -> EvidenceCard:
        abstract = source.abstract
        methodology = self._infer_methodology(abstract, source.provider)
        limitations = self._infer_limitations(abstract, source.provider)
        stance = self._infer_stance(abstract)
        strength = self._infer_strength(methodology, source.provider)
        claim = abstract.split(".")[0].strip() or source.title
        findings = ". ".join(segment.strip() for segment in abstract.split(".")[:2] if segment.strip()) or abstract
        highlight = findings[:220]
        return EvidenceCard(
            source_id=source.id,
            source_title=source.title,
            provider=source.provider,
            claim=claim,
            methodology=methodology,
            findings=findings,
            limitations=limitations,
            stance=stance,
            evidence_strength=strength,
            highlight=highlight,
        )

    def _fallback_critique(
        self,
        evidence_cards: list[EvidenceCard],
        simulated_research: bool,
    ) -> dict[str, Any]:
        contradictions: list[dict[str, Any]] = []
        stances = {card.stance for card in evidence_cards}
        if "supports" in stances and "questions" in stances:
            contradictions.append(
                {
                    "summary": "Supportive and skeptical sources diverge on the size or consistency of the effect.",
                    "explanation": "Some papers report a positive signal while others emphasize null or context-dependent results.",
                    "severity": "high",
                    "source_ids": [card.source_id for card in evidence_cards[:3]],
                }
            )
        elif "mixed" in stances:
            contradictions.append(
                {
                    "summary": "Several sources report mixed or conditional outcomes.",
                    "explanation": "The evidence appears sensitive to setting, population, or methodology.",
                    "severity": "medium",
                    "source_ids": [card.source_id for card in evidence_cards[:2]],
                }
            )
        limitations = []
        for card in evidence_cards:
            limitations.extend(card.limitations)
        limitations.append("Most analysis is abstract-level rather than full-text review.")
        if simulated_research:
            limitations.append("Using simulated academic results because live research sources were unavailable.")
        return {
            "contradiction_cards": contradictions,
            "limitations": list(dict.fromkeys(limitations)),
            "debate_summary": (
                "Critic found meaningful uncertainty in the evidence base and flagged the most important caveats."
            ),
        }

    def _fallback_synthesis(
        self,
        question: str,
        evidence_cards: list[EvidenceCard],
        contradiction_cards: list[ContradictionCard],
        heuristic_score: float,
        pass_index: int,
    ) -> dict[str, Any]:
        support_count = sum(card.stance == "supports" for card in evidence_cards)
        question_count = sum(card.stance == "questions" for card in evidence_cards)
        mixed_count = sum(card.stance == "mixed" for card in evidence_cards)
        if support_count > question_count + mixed_count:
            verdict = f"The council finds the evidence generally supportive on '{question}', but not definitive."
        elif question_count > support_count:
            verdict = f"The council finds the evidence too weak or inconsistent to strongly support '{question}'."
        else:
            verdict = f"The council finds the evidence mixed on '{question}', with real signal but meaningful uncertainty."

        supporting_evidence = [
            f"{card.source_title}: {card.findings[:140]}" for card in evidence_cards[:3]
        ]
        limitations = list(dict.fromkeys([limit for card in evidence_cards for limit in card.limitations]))
        limitations.append("The council worked from metadata, abstracts, and API-available summaries.")
        next_steps = [
            "Retrieve full-text papers for the strongest and weakest studies.",
            "Validate whether the reported effect holds across populations or benchmark settings.",
            "Run a targeted second-stage search focused on contradiction resolution.",
        ]
        contradiction_count = len(contradiction_cards)
        council_summary = (
            f"Pass {pass_index} concludes with {len(evidence_cards)} evidence cards and {contradiction_count} contradiction checks."
        )
        return {
            "final_verdict": verdict,
            "confidence_score": round(heuristic_score, 2),
            "supporting_evidence": supporting_evidence,
            "recommended_next_steps": next_steps,
            "limitations": limitations,
            "council_summary": council_summary,
        }

    def _fallback_gap_finder(
        self,
        evidence_cards: list[EvidenceCard],
        contradiction_cards: list[ContradictionCard],
        limitations: list[str],
    ) -> dict[str, Any]:
        gaps = []
        if contradiction_cards:
            gaps.append(
                f"The contradiction between '{contradiction_cards[0].summary}' remains unresolved and needs targeted follow-up."
            )
        if any(card.evidence_strength == "preliminary" for card in evidence_cards):
            gaps.append(
                "Multiple sources rated 'preliminary' — larger, peer-reviewed replications are absent from the evidence base."
            )
        if limitations:
            gaps.append(
                f"Key limitation not yet addressed by any source: {limitations[0]}"
            )
        gaps.append("No longitudinal evidence was found to assess long-term stability of the reported effects.")
        gaps.append(
            "Evidence coverage skews toward English-language Western contexts; cross-cultural replication is unknown."
        )
        gap_summary = (
            "The current evidence base contains meaningful gaps in replication, longitudinal follow-up, "
            "and cross-contextual validation that prevent a fully confident verdict."
        )
        return {
            "research_gaps": gaps[:5],
            "gap_summary": gap_summary,
        }

    def _fallback_archivist(self, sources: list[SourceRecord]) -> dict[str, Any]:
        citations = []
        for source in sources:
            authors_str = ", ".join(source.authors[:3]) or "Unknown Author"
            if len(source.authors) > 3:
                authors_str += " et al."
            year_str = f"({source.year})" if source.year else "(n.d.)"
            venue_str = f" {source.venue}." if source.venue else ""
            url_str = f" {source.url}" if source.url else ""
            citations.append(f"{authors_str}. {year_str}. {source.title}.{venue_str}{url_str}")
        return {
            "formatted_citations": citations,
            "archive_summary": f"Archivist formatted {len(citations)} APA-style citations for this research session.",
        }

    # ── Scoring & Inference ────────────────────────────────────────────────────

    def _confidence_score(
        self,
        *,
        evidence_cards: list[EvidenceCard],
        contradiction_cards: list[ContradictionCard],
        pass_index: int,
        simulated: bool,
    ) -> float:
        score = 0.38
        score += min(len(evidence_cards), 6) * 0.04
        score += sum(0.04 for card in evidence_cards if card.evidence_strength == "high")
        score += sum(0.02 for card in evidence_cards if card.evidence_strength == "moderate")
        score -= sum(0.07 for card in contradiction_cards if card.severity == "high")
        score -= sum(0.04 for card in contradiction_cards if card.severity == "medium")
        score -= sum(0.02 for card in contradiction_cards if card.severity == "low")
        score += min((pass_index - 1) * 0.05, 0.08)
        if simulated:
            score -= 0.12
        return round(max(0.35, min(score, 0.93)), 2)

    def _infer_methodology(self, abstract: str, provider: str) -> str:
        lower = abstract.lower()
        if "meta-analysis" in lower or "systematic review" in lower:
            return "Systematic review or meta-analysis"
        if "randomized" in lower or "controlled trial" in lower:
            return "Randomized or controlled experimental study"
        if "survey" in lower or "cross-sectional" in lower:
            return "Survey or cross-sectional study"
        if "benchmark" in lower or "evaluation" in lower:
            return "Benchmark or evaluation study"
        if provider == "arxiv":
            return "Preprint analysis or technical report"
        if provider == "simulated":
            return "Simulated evidence brief for demo mode"
        return "Observational or general empirical study"

    def _infer_limitations(self, abstract: str, provider: str) -> list[str]:
        lower = abstract.lower()
        limitations = []
        if provider == "arxiv":
            limitations.append("Preprint source may not be peer reviewed yet.")
        if provider == "simulated":
            limitations.append("Simulated academic result used only for demo mode.")
        if "small sample" in lower or "pilot" in lower:
            limitations.append("Likely limited by small-sample or pilot-study scope.")
        if "future work" in lower or "further research" in lower:
            limitations.append("Authors note meaningful follow-up work is still needed.")
        if not limitations:
            limitations.append("Abstract does not provide enough detail to fully assess causal strength.")
        return limitations

    def _infer_stance(self, abstract: str) -> Literal["supports", "mixed", "questions", "neutral"]:
        lower = abstract.lower()
        positive_markers = ["improve", "increase", "effective", "outperform", "associated with", "benefit"]
        skeptical_markers = ["no significant", "null", "limited", "insufficient", "unclear", "inconclusive"]
        if any(marker in lower for marker in positive_markers) and any(marker in lower for marker in skeptical_markers):
            return "mixed"
        if any(marker in lower for marker in skeptical_markers):
            return "questions"
        if any(marker in lower for marker in positive_markers):
            return "supports"
        return "neutral"

    def _infer_strength(self, methodology: str, provider: str) -> Literal["high", "moderate", "preliminary"]:
        if "Systematic review" in methodology or "meta-analysis" in methodology:
            return "high"
        if "Randomized" in methodology or "Benchmark" in methodology or "Observational" in methodology:
            return "moderate"
        if provider in {"arxiv", "simulated"}:
            return "preliminary"
        return "preliminary"

    def _event(
        self,
        *,
        agent: str,
        stage: Literal["planning", "retrieval", "reading", "critique", "synthesis", "retry", "system"],
        status: Literal["working", "complete", "retry", "error", "pending"],
        title: str,
        detail: str,
        pass_index: int,
    ) -> dict[str, Any]:
        return TimelineEvent(
            agent=agent,
            stage=stage,
            status=status,
            title=title,
            detail=detail,
            pass_index=pass_index,
        ).model_dump(mode="json")

    def _state_patch(self, state: CouncilState) -> dict[str, Any]:
        return {
            "investigation_plan": state.get("investigation_plan", []),
            "sources": state.get("sources", []),
            "evidence_cards": state.get("evidence_cards", []),
            "contradiction_cards": state.get("contradiction_cards", []),
            "research_gaps": state.get("research_gaps", []),
            "gap_summary": state.get("gap_summary", ""),
            "has_critical_gaps": state.get("has_critical_gaps", False),
            "formatted_citations": state.get("formatted_citations", []),
            "previous_related_queries": state.get("previous_related_queries", []),
        }
