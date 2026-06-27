# QUORUM — AI Research Council

![React](https://img.shields.io/badge/React-19-blue?logo=react)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-green?logo=fastapi)
![LangGraph](https://img.shields.io/badge/LangGraph-Multi--Agent-orange)
![TypeScript](https://img.shields.io/badge/TypeScript-5-blue?logo=typescript)
![License](https://img.shields.io/badge/License-MIT-lightgrey)

> **Don't ask a chatbot. Convene a council.**

QUORUM is an autonomous multi-agent research system that dispatches seven specialized AI agents to investigate a research question, autonomously retries when confidence is insufficient, and delivers a structured committee verdict with citations, contradiction analysis, and research gap identification.

---

## Architecture

QUORUM uses a **LangGraph StateGraph** to orchestrate seven specialized agents in a directed pipeline with a conditional retry loop:

```
Chair → Scout → Reader → Critic → Synthesizer → Gap-Finder → Archivist
                                                                     ↓
                                            Chair ← retry ← [confidence check]
```

| Agent | Stage | Responsibility |
|-------|-------|---------------|
| **Chair** | Planning | Decomposes the research question into sub-questions and search queries. On retry, incorporates previous contradictions and limitations to sharpen the plan. |
| **Scout** | Retrieval | Queries Semantic Scholar, arXiv, and CrossRef in parallel. Ranks results via vector similarity (ChromaDB). Falls back to labeled demo sources if all APIs fail. |
| **Reader** | Reading | Extracts structured evidence cards from each source: claim, methodology, findings, limitations, stance, and evidence strength. |
| **Critic** | Critique | Identifies contradictions, weak evidence, and missing information. Produces contradiction cards with severity ratings. |
| **Synthesizer** | Synthesis | Delivers a committee-style verdict with a computed confidence score (heuristic + LLM-adjusted), supporting evidence, limitations, and next steps. |
| **Gap-Finder** | Synthesis | Identifies 3–5 specific, meaningful research gaps that are unanswered, weak, or conflicting. Flags critical gaps that trigger retry. |
| **Archivist** | System | Formats all sources as APA-style citations. Queries the vector store for related past research. Archives the session. |

### Retry Loop

After the Archivist completes, the Chair evaluates **five retry conditions** (any one triggers retry):
1. Confidence score below the configured threshold
2. Fewer than 4 valid sources retrieved
3. More than 2 high-severity contradictions unresolved
4. Gap-Finder flagged critical unanswered gaps
5. All evidence cards rated "preliminary" strength

A hard `max_passes` limit (default: 2, max: 3) prevents infinite loops.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Agent Orchestration | LangGraph `StateGraph` with `CouncilState` TypedDict |
| Backend API | FastAPI + SQLite (query state) |
| Vector Store | ChromaDB (source embeddings for ranking & related research) |
| Research APIs | Semantic Scholar, arXiv, CrossRef |
| LLM Client | Custom `JsonLlmClient` (OpenAI-compatible) |
| Frontend | React + TypeScript + Tailwind CSS + Vite |
| Deployment | Docker + docker-compose |

---

## Quickstart

### Prerequisites

- Docker and docker-compose
- An OpenAI-compatible LLM API key (or any OpenAI-compatible provider)

### 1. Clone and configure

```bash
git clone https://github.com/your-org/quorum.git
cd quorum
cp .env.example .env
# Edit .env and set LLM_API_KEY
```

### 2. Start with docker-compose

```bash
docker-compose up --build
```

The frontend will be available at **http://localhost:4173**.
The backend API will be available at **http://localhost:8000**.

### 3. Run a query

Open http://localhost:4173, type a research question, configure the confidence gate and max passes, then click **Convene Council**.

### Stopping

```bash
docker-compose down
```

### Development (without Docker)

**Backend:**
```bash
cd backend
pip install -r requirements.txt
LLM_API_KEY=your-key uvicorn app.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

---

## Live vs Demo Mode

| Mode | When | Sources |
|------|------|---------|
| **Live** | LLM API key set and at least one research API responds | Real papers from Semantic Scholar, arXiv, CrossRef |
| **Demo** | All research APIs unavailable (rate limits, network issues) | Clearly labeled simulated academic briefs |

Demo mode is a graceful fallback — the council still runs all seven agents, but sources are labeled `simulated` and the UI shows a prominent warning banner. The confidence score is penalized by 12 percentage points in demo mode.

To force demo mode (for testing), set `ENABLE_DEMO_MODE=true` and unset `SEMANTIC_SCHOLAR_API_KEY`.

---

## Configuration

All settings are in `.env` (see `.env.example`):

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_API_KEY` | — | OpenAI-compatible API key |
| `LLM_BASE_URL` | `https://api.openai.com/v1` | LLM provider base URL |
| `LLM_MODEL` | `gpt-4.1-mini` | Model to use |
| `SEMANTIC_SCHOLAR_API_KEY` | — | Optional; increases rate limits |
| `DEFAULT_CONFIDENCE_THRESHOLD` | `0.74` | Confidence gate for retry |
| `MAX_RESEARCH_PASSES` | `2` | Hard limit on retry passes |
| `ENABLE_DEMO_MODE` | `true` | Fall back to demo sources if live APIs fail |
| `FRONTEND_ORIGIN` | `http://localhost:4173` | CORS allowed origin |

---

## API Reference

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/query` | Start a new research session |
| `GET` | `/api/query/{id}/status` | Poll for agent progress, timeline, evidence cards |
| `GET` | `/api/query/{id}/result` | Retrieve the final verdict payload when complete |
| `GET` | `/health` | Health check |

---

## Project Structure

```
quorum/
├── backend/
│   ├── app/
│   │   ├── graph.py          # All 7 agents + LangGraph wiring
│   │   ├── schemas.py        # Pydantic models for all API types
│   │   ├── main.py           # FastAPI routes
│   │   ├── db.py             # SQLite repository
│   │   ├── config.py         # Settings via pydantic-settings
│   │   └── services/
│   │       ├── llm.py        # JsonLlmClient
│   │       ├── research.py   # Semantic Scholar + arXiv + CrossRef
│   │       └── vector_store.py # ChromaDB integration
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── App.tsx           # Full UI with all result sections
│       ├── types.ts          # TypeScript types
│       └── api.ts            # API client
├── docker-compose.yml
└── .env.example
```
