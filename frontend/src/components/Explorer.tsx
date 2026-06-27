import { forwardRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { QueryStatus, VerdictPayload } from "../types";
import {
  EvidenceCard,
  ContradictionCard,
  SourceRecord,
  InvestigationStep,
} from "../types";
import { Empty, Pill, providerLabel } from "./primitives";

type Tab =
  | "evidence"
  | "contradictions"
  | "gaps"
  | "plan"
  | "sources"
  | "citations"
  | "transcript"
  | "related";

type Props = {
  result: VerdictPayload;
  status: QueryStatus | null;
};

export const Explorer = forwardRef<HTMLDivElement, Props>(function Explorer(
  { result, status },
  ref
) {
  const evidence = result.evidence_cards ?? [];
  const contradictions = result.contradiction_cards ?? [];
  const sources = result.sources ?? [];
  const gaps = result.research_gaps ?? [];
  const citations = result.formatted_citations ?? [];
  const related = result.previous_related_queries ?? [];
  const plan = status?.investigation_plan ?? [];
  const transcript = status?.timeline ?? [];

  const tabs: { key: Tab; label: string; count: number; hidden?: boolean }[] = [
    { key: "evidence", label: "Evidence", count: evidence.length },
    { key: "contradictions", label: "Contradictions", count: contradictions.length },
    { key: "gaps", label: "Gaps", count: gaps.length },
    { key: "plan", label: "Plan", count: plan.length },
    { key: "sources", label: "Sources", count: sources.length },
    { key: "citations", label: "Citations", count: citations.length },
    { key: "transcript", label: "Transcript", count: transcript.length },
    { key: "related", label: "Related", count: related.length, hidden: related.length === 0 },
  ];

  const [active, setActive] = useState<Tab>("evidence");
  const visibleTabs = tabs.filter((t) => !t.hidden);

  return (
    <section
      ref={ref}
      className="mx-auto w-full max-w-[1280px] px-4 pb-24 sm:px-6"
    >
      {/* Section header */}
      <div className="mb-5 flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="eyebrow">Evidence explorer</p>
          <h3 className="mt-1 font-display text-3xl text-ember">
            Trace every claim back to its source.
          </h3>
        </div>
      </div>

      {/* Tab bar */}
      <div className="surface-raised mb-4 flex gap-1 overflow-x-auto rounded-2xl p-1.5">
        {visibleTabs.map((t) => {
          const isActive = active === t.key;
          return (
            <button
              key={t.key}
              onClick={() => setActive(t.key)}
              className={`relative flex shrink-0 items-center gap-2 rounded-xl px-3.5 py-2 text-[13px] font-medium transition ${
                isActive ? "text-ember" : "text-slate-400 hover:text-ember"
              }`}
            >
              {isActive && (
                <motion.span
                  layoutId="tab-pill"
                  transition={{ type: "spring", duration: 0.5, bounce: 0.18 }}
                  className="absolute inset-0 rounded-xl bg-brass/15 shadow-[inset_0_0_0_1px_rgba(212,164,74,0.3)]"
                />
              )}
              <span className="relative">{t.label}</span>
              <span
                className={`relative rounded-full px-1.5 text-[10px] font-mono ${
                  isActive ? "bg-brass/25 text-ember" : "bg-white/5 text-slate-500"
                }`}
              >
                {t.count}
              </span>
            </button>
          );
        })}
      </div>

      {/* Panels */}
      <AnimatePresence mode="wait">
        <motion.div
          key={active}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -4 }}
          transition={{ duration: 0.3 }}
        >
          {active === "evidence" && <EvidencePanel cards={evidence} sources={sources} />}
          {active === "contradictions" && <ContradictionsPanel cards={contradictions} />}
          {active === "gaps" && (
            <GapsPanel
              gaps={gaps}
              summary={result.gap_summary}
              critical={result.has_critical_gaps}
              nextSteps={result.recommended_next_steps}
            />
          )}
          {active === "plan" && <PlanPanel steps={plan} />}
          {active === "sources" && <SourcesPanel sources={sources} />}
          {active === "citations" && <CitationsPanel citations={citations} />}
          {active === "transcript" && <TranscriptPanel events={transcript} />}
          {active === "related" && <RelatedPanel related={related} />}
        </motion.div>
      </AnimatePresence>
    </section>
  );
});

/* ─────────────────────── Evidence ─────────────────────── */
function EvidencePanel({
  cards,
  sources,
}: {
  cards: EvidenceCard[];
  sources: SourceRecord[];
}) {
  const [open, setOpen] = useState<string | null>(null);
  if (cards.length === 0) return <Empty copy="No evidence cards yet." />;

  const sourceById = new Map(sources.map((s) => [s.id, s]));

  return (
    <div className="grid gap-3 md:grid-cols-2">
      {cards.map((c, i) => {
        const id = `${c.source_id}-${i}`;
        const isOpen = open === id;
        const src = sourceById.get(c.source_id);
        return (
          <motion.article
            key={id}
            layout
            className="surface row-hover group rounded-2xl p-5"
          >
            <header className="flex flex-wrap items-center gap-2">
              <Pill
                label={c.stance}
                tone={
                  (c.stance === "supports"
                    ? "supports"
                    : c.stance === "questions"
                    ? "questions"
                    : c.stance === "mixed"
                    ? "mixed"
                    : "neutral") as never
                }
              />
              <Pill
                label={`${c.evidence_strength} strength`}
                tone={
                  (c.evidence_strength === "high"
                    ? "high"
                    : c.evidence_strength === "moderate"
                    ? "moderate"
                    : "preliminary") as never
                }
              />
              <span className="ml-auto text-[10px] font-mono uppercase tracking-widest text-slate-500">
                {providerLabel(c.provider)}
              </span>
            </header>

            <p className="mt-3 font-display text-lg leading-snug text-ember">{c.claim}</p>

            {c.highlight && (
              <blockquote className="mt-3 border-l-2 border-brass/40 pl-3 text-sm italic leading-6 text-slate-300/90">
                "{c.highlight}"
              </blockquote>
            )}

            <p className="mt-3 text-xs text-slate-500 line-clamp-1">
              <span className="text-slate-400">From:</span> {c.source_title}
            </p>

            <button
              onClick={() => setOpen(isOpen ? null : id)}
              className="mt-4 text-[11px] font-medium uppercase tracking-[0.2em] text-ember/80 transition hover:text-ember"
            >
              {isOpen ? "Hide details ↑" : "Show details ↓"}
            </button>

            <AnimatePresence initial={false}>
              {isOpen && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: "auto", opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
                  className="overflow-hidden"
                >
                  <div className="mt-4 space-y-3 border-t border-brass/12 pt-4">
                    <Detail label="Methodology" value={c.methodology} />
                    <Detail label="Findings" value={c.findings} />
                    {c.limitations?.length > 0 && (
                      <div>
                        <p className="eyebrow mb-1">Limitations</p>
                        <ul className="space-y-1 text-xs leading-5 text-slate-400">
                          {c.limitations.map((l, idx) => (
                            <li key={idx} className="flex gap-2">
                              <span className="text-brass/60">·</span>
                              {l}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {src && (
                      <div className="flex flex-wrap gap-2 pt-1">
                        {src.url && (
                          <a href={src.url} target="_blank" rel="noreferrer" className="btn-ghost">
                            Open source ↗
                          </a>
                        )}
                        {src.pdf_url && (
                          <a href={src.pdf_url} target="_blank" rel="noreferrer" className="btn-ghost">
                            PDF ↗
                          </a>
                        )}
                      </div>
                    )}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </motion.article>
        );
      })}
    </div>
  );
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="eyebrow mb-1">{label}</p>
      <p className="text-xs leading-6 text-slate-300/90">{value || "—"}</p>
    </div>
  );
}

/* ─────────────────────── Contradictions ─────────────────────── */
function ContradictionsPanel({ cards }: { cards: ContradictionCard[] }) {
  if (cards.length === 0) return <Empty copy="No contradictions detected." />;
  return (
    <div className="space-y-3">
      {cards.map((c, i) => (
        <motion.div
          key={i}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: i * 0.04 }}
          className="surface rounded-2xl p-5"
        >
          <div className="flex flex-wrap items-center gap-2">
            <Pill
              label={`${c.severity} severity`}
              tone={
                (c.severity === "high"
                  ? "danger"
                  : c.severity === "medium"
                  ? "warning"
                  : "neutral") as never
              }
            />
            <span className="text-[10px] font-mono text-slate-500">
              {c.source_ids.length} source{c.source_ids.length === 1 ? "" : "s"}
            </span>
          </div>
          <p className="mt-3 font-display text-lg leading-snug text-ember">{c.summary}</p>
          <p className="mt-2 text-sm leading-6 text-slate-400">{c.explanation}</p>
        </motion.div>
      ))}
    </div>
  );
}

/* ─────────────────────── Gaps ─────────────────────── */
function GapsPanel({
  gaps,
  summary,
  critical,
  nextSteps,
}: {
  gaps: string[];
  summary: string;
  critical: boolean;
  nextSteps: string[];
}) {
  if (gaps.length === 0 && nextSteps.length === 0)
    return <Empty copy="No research gaps reported." />;

  return (
    <div className="grid gap-4 lg:grid-cols-[1.4fr_1fr]">
      <div className="surface rounded-2xl p-6">
        <div className="flex items-center gap-2">
          {critical && <Pill label="Critical gaps" tone="danger" />}
          <p className="eyebrow">Research gaps</p>
        </div>
        {summary && <p className="mt-3 text-sm leading-6 text-slate-300/90">{summary}</p>}
        <ul className="mt-5 space-y-3">
          {gaps.map((g, i) => (
            <li
              key={i}
              className="flex gap-3 rounded-xl border border-brass/12 bg-abyss/40 p-3"
            >
              <span className="font-mono text-xs text-brass/70">0{i + 1}</span>
              <span className="text-sm leading-6 text-slate-300">{g}</span>
            </li>
          ))}
        </ul>
      </div>
      <div className="surface rounded-2xl p-6">
        <p className="eyebrow">Recommended next steps</p>
        {nextSteps.length === 0 ? (
          <p className="mt-3 text-sm text-slate-500">No next steps proposed.</p>
        ) : (
          <ol className="mt-4 space-y-3">
            {nextSteps.map((s, i) => (
              <li key={i} className="flex gap-3">
                <span className="grid h-6 w-6 shrink-0 place-items-center rounded-full bg-brass/15 font-mono text-[11px] text-ember">
                  {i + 1}
                </span>
                <p className="text-sm leading-6 text-slate-300">{s}</p>
              </li>
            ))}
          </ol>
        )}
      </div>
    </div>
  );
}

/* ─────────────────────── Plan ─────────────────────── */
function PlanPanel({ steps }: { steps: InvestigationStep[] }) {
  if (steps.length === 0) return <Empty copy="No investigation plan recorded." />;
  return (
    <div className="space-y-3">
      {steps.map((s, i) => (
        <motion.div
          key={i}
          initial={{ opacity: 0, x: -8 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: i * 0.06 }}
          className="surface rounded-2xl p-5"
        >
          <div className="flex items-center gap-3">
            <span className="grid h-8 w-8 place-items-center rounded-full border border-brass/30 bg-brass/10 font-mono text-xs text-ember">
              {String(i + 1).padStart(2, "0")}
            </span>
            <p className="font-display text-lg text-ember">{s.focus}</p>
          </div>
          <div className="mt-3 grid gap-3 sm:grid-cols-[1fr_auto] sm:items-start">
            <ul className="space-y-1 text-sm leading-6 text-slate-300">
              {s.key_questions.map((q, qi) => (
                <li key={qi} className="flex gap-2">
                  <span className="text-brass/60">›</span>
                  {q}
                </li>
              ))}
            </ul>
            {s.search_query && (
              <code className="surface-flat block rounded-lg px-3 py-2 font-mono text-[11px] text-ember">
                {s.search_query}
              </code>
            )}
          </div>
        </motion.div>
      ))}
    </div>
  );
}

/* ─────────────────────── Sources ─────────────────────── */
function SourcesPanel({ sources }: { sources: SourceRecord[] }) {
  if (sources.length === 0) return <Empty copy="No sources retrieved." />;
  return (
    <div className="grid gap-3 lg:grid-cols-2">
      {sources.map((s) => (
        <article
          key={s.id}
          className="surface row-hover group flex flex-col rounded-2xl p-5"
        >
          <div className="flex flex-wrap items-center gap-2">
            <Pill label={providerLabel(s.provider)} tone="gold" />
            {s.simulated && <Pill label="Simulated" tone="warning" />}
            {s.year && <span className="text-[11px] font-mono text-slate-500">{s.year}</span>}
            {s.citation_count !== null && (
              <span className="text-[11px] font-mono text-slate-500">
                · {s.citation_count} cites
              </span>
            )}
            <span className="ml-auto text-[10px] font-mono text-slate-600">
              {Math.round(s.relevance_score * 100)}% relevance
            </span>
          </div>
          <p className="mt-3 font-display text-lg leading-snug text-ember">{s.title}</p>
          {s.venue && <p className="mt-1 text-xs italic text-slate-400">{s.venue}</p>}
          {s.authors?.length > 0 && (
            <p className="mt-1.5 text-xs text-slate-500 line-clamp-1">
              {s.authors.slice(0, 5).join(", ")}
              {s.authors.length > 5 ? " et al." : ""}
            </p>
          )}
          {s.abstract && (
            <p className="mt-3 text-xs leading-5 text-slate-400 line-clamp-3">{s.abstract}</p>
          )}
          <div className="mt-4 flex gap-2 pt-1">
            {s.url && (
              <a href={s.url} target="_blank" rel="noreferrer" className="btn-ghost">
                Source ↗
              </a>
            )}
            {s.pdf_url && (
              <a href={s.pdf_url} target="_blank" rel="noreferrer" className="btn-ghost">
                PDF ↗
              </a>
            )}
          </div>
        </article>
      ))}
    </div>
  );
}

/* ─────────────────────── Citations ─────────────────────── */
function CitationsPanel({ citations }: { citations: string[] }) {
  if (citations.length === 0) return <Empty copy="No citations formatted." />;
  return (
    <div className="surface rounded-2xl p-6">
      <ol className="space-y-3">
        {citations.map((c, i) => (
          <li key={i} className="flex gap-3 border-b border-brass/10 pb-3 last:border-0">
            <span className="font-mono text-xs text-brass/60">[{i + 1}]</span>
            <p className="text-sm leading-6 text-slate-300">{c}</p>
          </li>
        ))}
      </ol>
    </div>
  );
}

/* ─────────────────────── Transcript ─────────────────────── */
function TranscriptPanel({ events }: { events: QueryStatus["timeline"] }) {
  if (events.length === 0) return <Empty copy="No transcript events." />;
  return (
    <div className="surface rounded-2xl p-6 overflow-hidden">
      <ol className="relative space-y-3 border-l border-brass/12 pl-5">
        {events.map((ev, i) => (
          <li key={i} className="relative min-w-0">
            <span className="absolute -left-[27px] top-1.5 h-2 w-2 rounded-full bg-brass/50" />
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-[11px] font-mono uppercase tracking-widest text-slate-500">
                {ev.agent}
              </span>
              <Pill
                label={ev.status}
                tone={
                  (ev.status === "error"
                    ? "danger"
                    : ev.status === "retry"
                    ? "warning"
                    : ev.status === "complete"
                    ? "supports"
                    : "gold") as never
                }
              />
              {ev.pass_index > 0 && (
                <span className="text-[10px] font-mono text-slate-600">
                  pass {ev.pass_index}
                </span>
              )}
              <span className="ml-auto text-[10px] font-mono text-slate-600">
                {new Date(ev.timestamp).toLocaleTimeString()}
              </span>
            </div>
            <p className="mt-1 text-sm leading-5 text-ember">{ev.title}</p>
            {ev.detail && (
              <p className="mt-0.5 text-xs leading-5 text-slate-500 break-words overflow-hidden">
                {ev.detail}
              </p>
            )}
          </li>
        ))}
      </ol>
    </div>
  );
}

/* ─────────────────────── Related ─────────────────────── */
function RelatedPanel({ related }: { related: string[] }) {
  return (
    <div className="surface rounded-2xl p-6">
      <p className="eyebrow mb-3">Previously asked</p>
      <ul className="space-y-2">
        {related.map((q, i) => (
          <li
            key={i}
            className="row-hover rounded-xl border border-brass/10 bg-abyss/40 p-3 text-sm text-slate-300"
          >
            {q}
          </li>
        ))}
      </ul>
    </div>
  );
}
