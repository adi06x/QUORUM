import { ReactNode } from "react";

/* ─────────────────────── Agent registry ─────────────────────── */
export type AgentKey =
  | "chair"
  | "scout"
  | "reader"
  | "critic"
  | "synthesizer"
  | "gap"
  | "archivist";

export const AGENTS: Record<
  AgentKey,
  { name: string; role: string; glyph: string; stages: string[] }
> = {
  chair: { name: "Chair", role: "Convenes the council", glyph: "◆", stages: ["planning", "system"] },
  scout: { name: "Scout", role: "Retrieves the literature", glyph: "✦", stages: ["retrieval"] },
  reader: { name: "Reader", role: "Reads and extracts evidence", glyph: "❖", stages: ["reading"] },
  critic: { name: "Critic", role: "Stress-tests every claim", glyph: "✶", stages: ["critique", "retry"] },
  synthesizer: { name: "Synthesizer", role: "Assembles the verdict", glyph: "✷", stages: ["synthesis"] },
  gap: { name: "Gap-Finder", role: "Surfaces what is missing", glyph: "◇", stages: ["synthesis"] },
  archivist: { name: "Archivist", role: "Curates citations & history", glyph: "✧", stages: ["synthesis"] },
};

export const AGENT_ORDER: AgentKey[] = [
  "chair",
  "scout",
  "reader",
  "critic",
  "synthesizer",
  "gap",
  "archivist",
];

export function agentForStage(stage: string): AgentKey {
  const s = (stage || "").toLowerCase();
  for (const key of AGENT_ORDER) {
    if (AGENTS[key].stages.includes(s)) return key;
  }
  return "chair";
}

/* ─────────────────────── Tones / pills ─────────────────────── */
export function Pill({
  label,
  tone = "neutral",
  className = "",
}: {
  label: string;
  tone?:
    | "supports"
    | "questions"
    | "mixed"
    | "neutral"
    | "high"
    | "moderate"
    | "preliminary"
    | "gold"
    | "danger"
    | "warning";
  className?: string;
}) {
  const cls = {
    supports: "border-emerald-500/30 bg-emerald-500/10 text-emerald-300",
    questions: "border-amber-500/30 bg-amber-500/10 text-amber-300",
    mixed: "border-orange-500/30 bg-orange-500/10 text-orange-300",
    neutral: "border-slate-600/40 bg-white/5 text-slate-300",
    high: "border-emerald-500/30 bg-emerald-500/10 text-emerald-300",
    moderate: "border-amber-500/30 bg-amber-500/10 text-amber-300",
    preliminary: "border-slate-600/40 bg-white/5 text-slate-300",
    gold: "border-brass/40 bg-brass/10 text-ember",
    danger: "border-rose-500/30 bg-rose-500/10 text-rose-300",
    warning: "border-amber-500/30 bg-amber-500/10 text-amber-300",
  }[tone];

  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-[10px] font-medium uppercase tracking-[0.18em] ${cls} ${className}`}
    >
      {label}
    </span>
  );
}

/* ─────────────────────── Confidence ring ─────────────────────── */
export function ConfidenceRing({
  value,
  threshold,
  size = 220,
  stroke = 10,
  showLabel = true,
}: {
  value: number | null; // 0..1
  threshold?: number; // 0..1
  size?: number;
  stroke?: number;
  showLabel?: boolean;
}) {
  const pct = Math.max(0, Math.min(1, value ?? 0));
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const dash = c * pct;
  const thrAngle = threshold ? threshold * 360 : null;

  const color =
    value === null
      ? "#475569"
      : pct >= (threshold ?? 0.7)
      ? "#86efac"
      : pct >= 0.5
      ? "#f3d27a"
      : "#fca5a5";

  return (
    <div className="relative inline-flex items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <defs>
          <linearGradient id="confGrad" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="#f3d27a" />
            <stop offset="100%" stopColor="#d4a44a" />
          </linearGradient>
          <filter id="confGlow">
            <feGaussianBlur stdDeviation="2.5" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          stroke="rgba(212,164,74,0.10)"
          strokeWidth={stroke}
          fill="none"
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          stroke={value === null ? "rgba(255,255,255,0.06)" : "url(#confGrad)"}
          strokeWidth={stroke}
          strokeLinecap="round"
          fill="none"
          strokeDasharray={`${dash} ${c}`}
          style={{ transition: "stroke-dasharray 0.9s cubic-bezier(0.16,1,0.3,1)" }}
          filter={value !== null ? "url(#confGlow)" : undefined}
        />
        {thrAngle !== null && (
          <g transform={`rotate(${thrAngle - 90} ${size / 2} ${size / 2}) translate(${size / 2} ${stroke / 2})`}>
            <line
              x1="0"
              y1="-4"
              x2="0"
              y2={stroke + 4}
              stroke="rgba(255,255,255,0.55)"
              strokeWidth="1.5"
            />
          </g>
        )}
      </svg>
      {showLabel && (
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <div className="font-display text-[clamp(2.8rem,5vw,4.2rem)] leading-none text-gold-grad">
            {value === null ? "—" : Math.round(pct * 100)}
          </div>
          <div className="mt-1 eyebrow" style={{ color: `${color}aa` }}>
            Confidence
          </div>
        </div>
      )}
    </div>
  );
}

/* ─────────────────────── Surface ─────────────────────── */
export function Card({
  children,
  className = "",
  raised = false,
}: {
  children: ReactNode;
  className?: string;
  raised?: boolean;
}) {
  return (
    <div className={`${raised ? "surface-raised" : "surface"} rounded-3xl ${className}`}>
      {children}
    </div>
  );
}

/* ─────────────────────── Eyebrow header ─────────────────────── */
export function EyebrowHeader({
  eyebrow,
  title,
  desc,
  right,
}: {
  eyebrow: string;
  title: string;
  desc?: string;
  right?: ReactNode;
}) {
  return (
    <div className="mb-5 flex items-start justify-between gap-4">
      <div>
        <p className="eyebrow">{eyebrow}</p>
        <p className="mt-1.5 font-display text-2xl text-ember">{title}</p>
        {desc && <p className="mt-1.5 text-sm leading-6 text-slate-400">{desc}</p>}
      </div>
      {right}
    </div>
  );
}

/* ─────────────────────── Empty ─────────────────────── */
export function Empty({ copy }: { copy: string }) {
  return (
    <div className="rounded-2xl border border-dashed border-slate-700/40 px-5 py-8 text-center text-sm text-slate-500">
      {copy}
    </div>
  );
}

/* ─────────────────────── Provider icon ─────────────────────── */
export function providerLabel(p: string): string {
  return {
    semantic_scholar: "Semantic Scholar",
    arxiv: "arXiv",
    crossref: "CrossRef",
    simulated: "Simulated",
  }[p] || p;
}
