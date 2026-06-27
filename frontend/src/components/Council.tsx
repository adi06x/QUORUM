import { useEffect, useMemo, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { QueryStatus } from "../types";
import {
  AGENTS,
  AGENT_ORDER,
  AgentKey,
  agentForStage,
  ConfidenceRing,
  Pill,
} from "./primitives";

type Props = {
  question: string;
  status: QueryStatus | null;
  threshold: number; // 0..1
  onCancel?: () => void;
};

const STAGE_LABEL: Record<string, string> = {
  queued: "Convening",
  planning: "Planning the inquiry",
  retrieval: "Retrieving literature",
  reading: "Reading & extracting evidence",
  critique: "Critiquing claims",
  synthesis: "Synthesizing verdict",
  retry: "Retrying research pass",
  system: "Coordinating",
  completed: "Quorum reached",
  failed: "Council halted",
};

export function Council({ question, status, threshold }: Props) {
  const stage = (status?.current_stage ?? "queued").toLowerCase();
  const activeAgent: AgentKey = agentForStage(stage);
  const passCount = status?.pass_count ?? 0;
  const maxPasses = status?.max_passes ?? 1;
  const confidence = status?.confidence_score ?? null;
  const timeline = status?.timeline ?? [];
  const message = status?.current_message ?? "";

  return (
    <motion.section
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
      className="mx-auto w-full max-w-[1280px] px-4 pt-8 pb-12 sm:px-6"
    >
      {/* Question header */}
      <div className="mb-6 flex flex-wrap items-center gap-3">
        <div className="tag">
          <span className="live-dot" />
          Council in session
        </div>
        <span className="text-xs text-slate-500">
          Pass <span className="font-mono text-ember">{Math.max(1, passCount)}</span> of {maxPasses} ·{" "}
          Threshold {Math.round(threshold * 100)}%
        </span>
      </div>
      <h2 className="font-display text-[clamp(1.6rem,3vw,2.6rem)] leading-tight text-ember">
        {question}
      </h2>

      {/* Main grid */}
      <div className="mt-8 grid gap-5 lg:grid-cols-[minmax(0,1fr)_420px]">
        {/* LEFT — Council orbit */}
        <div className="surface-raised relative overflow-hidden rounded-[28px] p-6 sm:p-8">
          <CouncilOrbit activeAgent={activeAgent} stage={stage} />

          {/* Stage caption */}
          <div className="relative z-10 mt-6 flex flex-col items-center text-center">
            <p className="eyebrow">Current stage</p>
            <p className="mt-1.5 font-display text-2xl text-ember">
              <span className="shimmer-text">{STAGE_LABEL[stage] ?? stage}</span>
            </p>
            <AnimatePresence mode="wait">
              <motion.p
                key={message}
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -6 }}
                transition={{ duration: 0.4 }}
                className="mt-2 max-w-md text-sm text-slate-400"
              >
                {message || "Initializing the council…"}
              </motion.p>
            </AnimatePresence>
          </div>

          {/* Pass progress */}
          <div className="mt-8 flex items-center justify-center gap-2">
            {Array.from({ length: maxPasses }).map((_, i) => {
              const done = i < passCount - 1 || status?.status === "completed";
              const cur = i === Math.max(0, passCount - 1) && status?.status !== "completed";
              return (
                <div
                  key={i}
                  className={`h-1.5 w-12 rounded-full transition ${
                    done
                      ? "bg-brass/70"
                      : cur
                      ? "bg-gradient-to-r from-brass to-ember animate-pulse"
                      : "bg-white/5"
                  }`}
                />
              );
            })}
          </div>
        </div>

        {/* RIGHT — Confidence + Live timeline */}
        <div className="flex min-w-0 flex-col gap-5">
          {/* Confidence */}
          <div className="surface-raised flex items-center gap-6 rounded-[24px] p-6">
            <ConfidenceRing
              value={confidence}
              threshold={threshold}
              size={140}
              stroke={8}
            />
            <div className="min-w-0 flex-1">
              <p className="eyebrow">Council confidence</p>
              <p className="mt-1 font-display text-2xl text-ember">
                {confidence === null
                  ? "Building…"
                  : `${Math.round(confidence * 100)}% · target ${Math.round(threshold * 100)}%`}
              </p>
              <p className="mt-2 text-xs leading-5 text-slate-500">
                Retries trigger automatically until evidence clears the threshold or passes are
                exhausted.
              </p>
            </div>
          </div>

          {/* Timeline */}
          <div className="surface-raised flex min-h-[320px] flex-col overflow-hidden rounded-[24px]">
            <div className="flex items-center justify-between border-b border-brass/10 px-5 py-3.5">
              <p className="eyebrow">Live transcript</p>
              <span className="text-[10px] font-mono text-slate-500">
                {timeline.length} event{timeline.length === 1 ? "" : "s"}
              </span>
            </div>
            <LiveTimeline timeline={timeline} activeAgent={activeAgent} />
          </div>
        </div>
      </div>
    </motion.section>
  );
}

/* ─────────────────────── Orbit ─────────────────────── */
function CouncilOrbit({ activeAgent, stage }: { activeAgent: AgentKey; stage: string }) {
  const isWorking = stage !== "completed" && stage !== "failed";
  const n = AGENT_ORDER.length;

  // Positions: percentages relative to the square container.
  const positions = useMemo(() => {
    const R_PCT = 38; // orbit radius as % of container
    return AGENT_ORDER.map((key, i) => {
      const angle = (i / n) * Math.PI * 2 - Math.PI / 2;
      return {
        key,
        x: 50 + R_PCT * Math.cos(angle),
        y: 50 + R_PCT * Math.sin(angle),
      };
    });
  }, [n]);

  return (
    <div className="relative mx-auto aspect-square w-full max-w-[520px]">
      {/* Ambient halo — double layer for depth */}
      <div className="pointer-events-none absolute inset-[-10%] -z-10 rounded-full bg-[radial-gradient(circle,rgba(212,164,74,0.15),transparent_60%)] blur-3xl halo" />
      <div className="pointer-events-none absolute inset-[10%] -z-10 rounded-full bg-[radial-gradient(circle,rgba(212,164,74,0.08),transparent_70%)] blur-2xl" />

      {/* Concentric rings — 4 rings now for more depth */}
      <motion.div
        animate={{ rotate: 360 }}
        transition={{ duration: 90, repeat: Infinity, ease: "linear" }}
        className="orbit-ring absolute inset-[3%] opacity-60"
      />
      <motion.div
        animate={{ rotate: -360 }}
        transition={{ duration: 130, repeat: Infinity, ease: "linear" }}
        className="orbit-ring-solid absolute inset-[14%]"
      />
      <motion.div
        animate={{ rotate: 360 }}
        transition={{ duration: 180, repeat: Infinity, ease: "linear" }}
        className="orbit-ring absolute inset-[24%] opacity-40"
      />
      <motion.div
        animate={{ rotate: -360 }}
        transition={{ duration: 55, repeat: Infinity, ease: "linear" }}
        className="orbit-ring absolute inset-[32%] opacity-30"
      />

      {/* Floating particles */}
      {isWorking && (
        <svg
          viewBox="0 0 100 100"
          className="pointer-events-none absolute inset-0 h-full w-full"
        >
          {[...Array(6)].map((_, i) => {
            const baseAngle = (i / 6) * 360;
            const r = 30 + (i % 3) * 7;
            const cx = 50 + r * Math.cos((baseAngle * Math.PI) / 180);
            const cy = 50 + r * Math.sin((baseAngle * Math.PI) / 180);
            return (
              <motion.circle
                key={i}
                cx={cx}
                cy={cy}
                r={0.6 + (i % 2) * 0.4}
                fill="rgba(243,210,122,0.7)"
                animate={{
                  opacity: [0, 0.9, 0],
                  r: [0.4, 1.1, 0.4],
                }}
                transition={{
                  duration: 2.2 + i * 0.4,
                  repeat: Infinity,
                  delay: i * 0.45,
                  ease: "easeInOut",
                }}
              />
            );
          })}
        </svg>
      )}

      {/* SVG connection lines from center to each agent */}
      <svg
        viewBox="0 0 100 100"
        preserveAspectRatio="none"
        className="pointer-events-none absolute inset-0 h-full w-full"
      >
        <defs>
          <radialGradient id="lineFade" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="rgba(243,210,122,0.55)" />
            <stop offset="100%" stopColor="rgba(243,210,122,0)" />
          </radialGradient>
          <filter id="glow">
            <feGaussianBlur stdDeviation="0.8" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>
        {positions.map(({ key, x, y }) => {
          const active = key === activeAgent && isWorking;
          return (
            <line
              key={key}
              x1={50}
              y1={50}
              x2={x}
              y2={y}
              stroke={active ? "rgba(243,210,122,0.85)" : "rgba(212,164,74,0.12)"}
              strokeWidth={active ? 0.55 : 0.2}
              strokeDasharray={active ? "1.6 1.4" : "0.6 1.6"}
              className={active ? "dash-flow" : ""}
              vectorEffect="non-scaling-stroke"
              filter={active ? "url(#glow)" : undefined}
            />
          );
        })}
      </svg>

      {/* Center sigil */}
      <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2">
        <motion.div
          animate={isWorking ? { scale: [1, 1.06, 1] } : { scale: 1 }}
          transition={{ duration: 3.2, repeat: Infinity, ease: "easeInOut" }}
          className="relative grid h-28 w-28 place-items-center rounded-full border border-brass/40 bg-gradient-to-br from-brass/25 via-brass/10 to-transparent shadow-[0_0_50px_rgba(243,210,122,0.18)]"
        >
          <span className="font-display text-[44px] leading-none text-gold-grad">Q</span>
          <div className="absolute -inset-4 -z-10 rounded-full bg-brass/20 blur-2xl" />
          {isWorking && (
            <>
              <motion.span
                className="absolute inset-0 rounded-full"
                initial={{ scale: 1, opacity: 0.45 }}
                animate={{ scale: 1.6, opacity: 0 }}
                transition={{ duration: 2.6, repeat: Infinity, ease: "easeOut" }}
                style={{ boxShadow: "0 0 0 1px rgba(243,210,122,0.55)" }}
              />
              <motion.span
                className="absolute inset-0 rounded-full"
                initial={{ scale: 1, opacity: 0.25 }}
                animate={{ scale: 2.2, opacity: 0 }}
                transition={{ duration: 3.2, repeat: Infinity, ease: "easeOut", delay: 0.8 }}
                style={{ boxShadow: "0 0 0 1px rgba(243,210,122,0.3)" }}
              />
            </>
          )}
        </motion.div>
      </div>

      {/* Agents */}
      {positions.map(({ key, x, y }, i) => {
        const agent = AGENTS[key];
        const active = key === activeAgent && isWorking;
        return (
          <motion.div
            key={key}
            initial={{ opacity: 0, scale: 0.85 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: i * 0.07, duration: 0.55, ease: [0.16, 1, 0.3, 1] }}
            className="absolute -translate-x-1/2 -translate-y-1/2"
            style={{ left: `${x}%`, top: `${y}%` }}
          >
            <div className="group relative">
              {/* Soft idle halo for every agent */}
              <div
                className={`pointer-events-none absolute -inset-3 rounded-full blur-xl transition-opacity ${
                  active
                    ? "bg-brass/40 opacity-90"
                    : "bg-brass/15 opacity-50 group-hover:opacity-80"
                }`}
              />

              {/* Active expanding rings */}
              {active && (
                <>
                  <motion.div
                    className="absolute inset-0 rounded-full"
                    initial={{ scale: 1, opacity: 0.75 }}
                    animate={{ scale: 2.2, opacity: 0 }}
                    transition={{ duration: 1.8, repeat: Infinity, ease: "easeOut" }}
                    style={{ boxShadow: "0 0 0 2px rgba(243,210,122,0.6)" }}
                  />
                  <motion.div
                    className="absolute inset-0 rounded-full"
                    initial={{ scale: 1, opacity: 0.55 }}
                    animate={{ scale: 3.0, opacity: 0 }}
                    transition={{ duration: 2.4, repeat: Infinity, ease: "easeOut", delay: 0.6 }}
                    style={{ boxShadow: "0 0 0 1.5px rgba(243,210,122,0.4)" }}
                  />
                  <motion.div
                    className="absolute inset-0 rounded-full"
                    initial={{ scale: 1, opacity: 0.3 }}
                    animate={{ scale: 3.8, opacity: 0 }}
                    transition={{ duration: 3.0, repeat: Infinity, ease: "easeOut", delay: 1.2 }}
                    style={{ boxShadow: "0 0 0 1px rgba(243,210,122,0.25)" }}
                  />
                </>
              )}

              {/* Avatar node — breathes idly */}
              <div
                className={`breathe relative grid h-16 w-16 cursor-default place-items-center rounded-full border backdrop-blur-xl transition-all duration-300 ${
                  active
                    ? "border-brass/70 bg-gradient-to-br from-brass/35 to-brass/5 shadow-[0_0_36px_rgba(243,210,122,0.55),inset_0_0_18px_rgba(243,210,122,0.18)]"
                    : "border-brass/20 bg-abyss/70 group-hover:border-brass/45 group-hover:bg-brass/10 group-hover:shadow-[0_0_22px_rgba(243,210,122,0.25)]"
                }`}
                style={{ animationDelay: `${i * 0.45}s` }}
              >
                <span
                  className={`font-display text-2xl transition-colors ${
                    active ? "text-ember" : "text-slate-300 group-hover:text-ember"
                  }`}
                >
                  {agent.glyph}
                </span>

                {/* Status indicator dot */}
                {active && (
                  <span className="absolute -right-0.5 -top-0.5 grid h-3.5 w-3.5 place-items-center rounded-full bg-emerald-400 ring-2 ring-abyss">
                    <span className="absolute inset-0 animate-ping rounded-full bg-emerald-400/60" />
                  </span>
                )}
              </div>

              {/* Label */}
              <div className="absolute left-1/2 top-full mt-2 -translate-x-1/2 whitespace-nowrap text-center">
                <p
                  className={`text-[10px] font-medium uppercase tracking-[0.2em] transition-colors ${
                    active ? "text-ember" : "text-slate-500 group-hover:text-ember/80"
                  }`}
                >
                  {agent.name}
                </p>
                {active && (
                  <motion.p
                    initial={{ opacity: 0, y: -2 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="mt-0.5 text-[9px] font-mono uppercase tracking-[0.18em] text-brass/70"
                  >
                    active
                  </motion.p>
                )}
              </div>
            </div>
          </motion.div>
        );
      })}
    </div>
  );
}

/* ─────────────────────── Live timeline ─────────────────────── */
function LiveTimeline({
  timeline,
  activeAgent: _activeAgent,
}: {
  timeline: QueryStatus["timeline"];
  activeAgent: AgentKey;
}) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [timeline.length]);

  if (timeline.length === 0) {
    return (
      <div className="flex flex-1 items-center justify-center px-6 py-10 text-center text-xs text-slate-500">
        Waiting for the first event…
      </div>
    );
  }

  return (
    <div
      ref={scrollRef}
      className="flex-1 space-y-2 overflow-y-auto px-4 py-3"
      style={{ maxHeight: 360 }}
    >
      <AnimatePresence initial={false}>
        {timeline.map((ev, i) => (
          <motion.div
            key={`${ev.timestamp}-${i}`}
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
            className="row-hover rounded-xl border border-brass/8 bg-abyss/40 px-3 py-2.5 min-w-0 overflow-hidden"
          >
            <div className="flex items-center gap-2 min-w-0">
              <span className="shrink-0 text-[10px] font-mono uppercase tracking-widest text-brass/70">
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
              <span className="ml-auto shrink-0 text-[10px] font-mono text-slate-600 tabular-nums">
                {new Date(ev.timestamp).toLocaleTimeString()}
              </span>
            </div>
            <p className="mt-1 text-sm leading-5 text-ember">{ev.title}</p>
            {ev.detail && (
              <p className="mt-0.5 text-[11px] leading-4 text-slate-500 line-clamp-2 break-words overflow-hidden">
                {ev.detail}
              </p>
            )}
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}
