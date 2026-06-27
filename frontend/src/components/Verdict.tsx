import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { QueryStatus, VerdictPayload } from "../types";
import { ConfidenceRing, Pill } from "./primitives";

type Props = {
  question: string;
  result: VerdictPayload;
  status: QueryStatus | null;
  onReset: () => void;
  onExplore: () => void;
};

/** Animated count-up from 0 → target over `duration` ms. */
function useCountUp(target: number, duration = 1600) {
  const [v, setV] = useState(0);
  useEffect(() => {
    let raf = 0;
    const start = performance.now();
    const tick = (now: number) => {
      const t = Math.min(1, (now - start) / duration);
      // ease-out-quint
      const eased = 1 - Math.pow(1 - t, 5);
      setV(target * eased);
      if (t < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [target, duration]);
  return v;
}

export function Verdict({ question, result, status, onReset, onExplore }: Props) {
  const conf = result.confidence_score;
  const threshold = status?.confidence_threshold ?? 0.74;
  const passed = conf >= threshold;
  const animatedConf = useCountUp(conf, 1700);

  const stats = [
    { label: "Passes", value: result.passes_completed },
    { label: "Sources", value: result.sources.length },
    { label: "Evidence", value: result.evidence_cards.length },
    { label: "Contradictions", value: result.contradiction_cards.length },
    { label: "Gaps", value: result.research_gaps?.length ?? 0 },
  ];

  return (
    <motion.section
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
      className="mx-auto w-full max-w-[1280px] px-4 pt-8 pb-10 sm:px-6"
    >
      {/* Question recap */}
      <div className="mb-6 grid grid-cols-[minmax(0,1fr)_auto] items-center gap-3 sm:flex sm:flex-wrap">
        <div className="flex min-w-0 items-center gap-3">
          <div className="tag shrink-0">
            <span
              className="live-dot"
              style={
                passed
                  ? { background: "#86efac" }
                  : { background: "#fca5a5" }
              }
            />
            {passed ? "Quorum reached" : "Below threshold"}
          </div>
          <span className="truncate text-xs text-slate-500">{question}</span>
        </div>
        <div className="flex gap-2 sm:ml-auto">
          <button onClick={onReset} className="btn-ghost">
            New inquiry
          </button>
          <button onClick={onExplore} className="btn-ghost">
            Open evidence →
          </button>
        </div>
      </div>

      {/* Hero verdict */}
      <div className="relative overflow-hidden rounded-[36px] border border-brass/20 bg-gradient-to-br from-[#102043] via-[#0a1428] to-[#060b18] p-6 shadow-[0_60px_180px_-40px_rgba(212,164,74,0.35)] sm:p-12">
        {/* Ambient glow */}
        <div className="pointer-events-none absolute -right-32 -top-32 h-[420px] w-[420px] rounded-full bg-brass/15 blur-[120px]" />
        <div className="pointer-events-none absolute -bottom-40 -left-20 h-[360px] w-[360px] rounded-full bg-indigo-500/10 blur-[120px]" />

        <div className="relative grid items-center gap-10 lg:grid-cols-[1fr_280px]">
          <div className="min-w-0">
            <motion.p
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1, duration: 0.5 }}
              className="eyebrow"
            >
              Verdict of the council
            </motion.p>

            <motion.p
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2, duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
              className="mt-3 font-display text-[clamp(2rem,4.4vw,3.6rem)] leading-[1.08] tracking-tight text-ember"
            >
              {result.final_verdict}
            </motion.p>

            {result.council_summary && (
              <motion.p
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.45, duration: 0.6 }}
                className="mt-5 max-w-[700px] text-[15px] leading-7 text-slate-300/90"
              >
                {result.council_summary}
              </motion.p>
            )}

            <motion.div
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.65, duration: 0.5 }}
              className="mt-6 flex flex-wrap gap-2"
            >
              {result.simulated_research && <Pill label="Simulated literature" tone="warning" />}
              {result.has_critical_gaps && <Pill label="Critical gaps present" tone="danger" />}
              <Pill
                label={`${result.passes_completed} pass${result.passes_completed === 1 ? "" : "es"}`}
                tone="neutral"
              />
              <Pill label={`Mode: ${result.mode}`} tone="neutral" />
            </motion.div>
          </div>

          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.28, duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
            className="mx-auto"
          >
            <ConfidenceRing value={animatedConf} threshold={threshold} size={240} stroke={12} />
            <p className="mt-2 text-center text-[11px] uppercase tracking-[0.28em] text-slate-500">
              Target threshold {Math.round(threshold * 100)}%
            </p>
          </motion.div>
        </div>

        {/* Stats strip */}
        <div className="relative mt-10 grid grid-cols-2 gap-px overflow-hidden rounded-2xl border border-brass/15 bg-brass/[0.04] sm:grid-cols-5">
          {stats.map((s, i) => (
            <motion.div
              key={s.label}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.55 + i * 0.06, duration: 0.45 }}
              className="bg-abyss/60 px-5 py-4"
            >
              <p className="font-display text-3xl text-ember tabular-nums">{s.value}</p>
              <p className="mt-0.5 text-[10px] uppercase tracking-[0.22em] text-slate-500">
                {s.label}
              </p>
            </motion.div>
          ))}
        </div>
      </div>

      {/* Supporting evidence / contradictions / next-steps quick reveal */}
      <div className="mt-6 grid gap-4 lg:grid-cols-3">
        <RevealList
          delay={0.85}
          eyebrow="Supporting evidence"
          tone="supports"
          items={result.supporting_evidence}
          empty="No supporting evidence summarized."
        />
        <RevealList
          delay={1.0}
          eyebrow="Contradictions"
          tone="questions"
          items={result.contradictions}
          empty="No contradictions surfaced."
        />
        <RevealList
          delay={1.15}
          eyebrow="Recommended next steps"
          tone="gold"
          items={result.recommended_next_steps}
          empty="No follow-ups recommended."
        />
      </div>
    </motion.section>
  );
}

function RevealList({
  eyebrow,
  items,
  empty,
  delay,
  tone,
}: {
  eyebrow: string;
  items: string[];
  empty: string;
  delay: number;
  tone: "supports" | "questions" | "gold";
}) {
  const dotCls =
    tone === "supports"
      ? "bg-emerald-400/80"
      : tone === "questions"
      ? "bg-amber-400/80"
      : "bg-brass/80";

  return (
    <motion.div
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay, duration: 0.55, ease: [0.16, 1, 0.3, 1] }}
      className="surface rounded-2xl p-5"
    >
      <p className="eyebrow mb-3">{eyebrow}</p>
      {items.length === 0 ? (
        <p className="text-xs text-slate-500">{empty}</p>
      ) : (
        <ul className="space-y-2.5">
          {items.slice(0, 6).map((it, i) => (
            <motion.li
              key={i}
              initial={{ opacity: 0, x: -6 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: delay + 0.1 + i * 0.06, duration: 0.4 }}
              className="flex gap-2.5 text-[13px] leading-5 text-slate-300"
            >
              <span className={`mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full ${dotCls}`} />
              <span>{it}</span>
            </motion.li>
          ))}
        </ul>
      )}
    </motion.div>
  );
}
