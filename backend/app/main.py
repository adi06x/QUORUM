from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.db import QueryRepository
from app.graph import QuorumCouncil
from app.schemas import (
    ContradictionCard,
    EvidenceCard,
    InvestigationStep,
    QueryCreatedResponse,
    QueryRequest,
    QueryResultEnvelope,
    QueryStatusResponse,
    SourceRecord,
    TimelineEvent,
    VerdictPayload,
)


settings = get_settings()
repo = QueryRepository(settings.sqlite_file)
council = QuorumCouncil(settings, repo)


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings.sqlite_file.parent.mkdir(parents=True, exist_ok=True)
    settings.chroma_dir.mkdir(parents=True, exist_ok=True)
    repo.init()
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin, "http://127.0.0.1:4173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.post(f"{settings.api_prefix}/query", response_model=QueryCreatedResponse)
async def create_query(request: QueryRequest) -> QueryCreatedResponse:
    query_id = str(uuid4())
    max_passes = request.max_passes or settings.max_research_passes
    threshold = request.confidence_threshold or settings.default_confidence_threshold
    row = repo.create_query(query_id, request, max_passes=max_passes, threshold=threshold)
    asyncio.create_task(council.run_query(query_id, request))
    return QueryCreatedResponse(id=query_id, status=row["status"], created_at=row["created_at"])


@app.get(f"{settings.api_prefix}/query/{{query_id}}/status", response_model=QueryStatusResponse)
async def get_query_status(query_id: str) -> QueryStatusResponse:
    row = repo.get_query(query_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Query not found")

    state = json.loads(row["state_json"] or "{}")
    timeline = [TimelineEvent.model_validate(item) for item in json.loads(row["timeline_json"] or "[]")]
    return QueryStatusResponse(
        id=row["id"],
        question=row["question"],
        status=row["status"],
        current_stage=row["current_stage"],
        current_message=row["current_message"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        pass_count=row["pass_count"],
        max_passes=row["max_passes"],
        confidence_threshold=row["confidence_threshold"],
        confidence_score=row["confidence_score"],
        mode=row["mode"],
        simulated_research=row["simulated_research"],
        timeline=timeline,
        investigation_plan=[InvestigationStep.model_validate(item) for item in state.get("investigation_plan", [])],
        sources=[SourceRecord.model_validate(item) for item in state.get("sources", [])],
        evidence_cards=[EvidenceCard.model_validate(item) for item in state.get("evidence_cards", [])],
        contradiction_cards=[ContradictionCard.model_validate(item) for item in state.get("contradiction_cards", [])],
    )


@app.get(f"{settings.api_prefix}/query/{{query_id}}/result", response_model=QueryResultEnvelope)
async def get_query_result(query_id: str) -> QueryResultEnvelope:
    row = repo.get_query(query_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Query not found")

    if row["status"] != "completed":
        return QueryResultEnvelope(
            id=row["id"],
            status=row["status"],
            ready=False,
            error_message=row["error_message"],
        )

    result_payload = json.loads(row["result_json"]) if row["result_json"] else None
    result = VerdictPayload.model_validate(result_payload) if result_payload else None
    return QueryResultEnvelope(
        id=row["id"],
        status=row["status"],
        ready=True,
        error_message=row["error_message"],
        result=result,
    )
