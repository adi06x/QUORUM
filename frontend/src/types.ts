export type TimelineEvent = {
  agent: string;
  stage: "planning" | "retrieval" | "reading" | "critique" | "synthesis" | "retry" | "system";
  status: "working" | "complete" | "retry" | "error" | "pending";
  title: string;
  detail: string;
  pass_index: number;
  timestamp: string;
};

export type InvestigationStep = {
  focus: string;
  key_questions: string[];
  search_query: string;
};

export type SourceRecord = {
  id: string;
  title: string;
  abstract: string;
  authors: string[];
  year: number | null;
  venue: string | null;
  url: string | null;
  pdf_url: string | null;
  provider: "semantic_scholar" | "arxiv" | "crossref" | "simulated";
  citation_count: number | null;
  relevance_score: number;
  simulated: boolean;
};

export type EvidenceCard = {
  source_id: string;
  source_title: string;
  provider: string;
  claim: string;
  methodology: string;
  findings: string;
  limitations: string[];
  stance: "supports" | "mixed" | "questions" | "neutral";
  evidence_strength: "high" | "moderate" | "preliminary";
  highlight: string;
};

export type ContradictionCard = {
  summary: string;
  explanation: string;
  severity: "high" | "medium" | "low";
  source_ids: string[];
};

export type QueryStatus = {
  id: string;
  question: string;
  status: "queued" | "running" | "completed" | "failed";
  current_stage: string;
  current_message: string;
  created_at: string;
  updated_at: string;
  pass_count: number;
  max_passes: number;
  confidence_threshold: number;
  confidence_score: number | null;
  mode: string;
  simulated_research: boolean;
  timeline: TimelineEvent[];
  investigation_plan: InvestigationStep[];
  sources: SourceRecord[];
  evidence_cards: EvidenceCard[];
  contradiction_cards: ContradictionCard[];
};

export type VerdictPayload = {
  final_verdict: string;
  confidence_score: number;
  supporting_evidence: string[];
  contradictions: string[];
  limitations: string[];
  recommended_next_steps: string[];
  sources: SourceRecord[];
  evidence_cards: EvidenceCard[];
  contradiction_cards: ContradictionCard[];
  mode: string;
  simulated_research: boolean;
  council_summary: string;
  passes_completed: number;
  // Gap-Finder
  research_gaps: string[];
  gap_summary: string;
  has_critical_gaps: boolean;
  // Archivist
  formatted_citations: string[];
  previous_related_queries: string[];
};

export type QueryResultEnvelope = {
  id: string;
  status: string;
  ready: boolean;
  error_message: string | null;
  result: VerdictPayload | null;
};
