import { FormEvent, useMemo } from "react";
import { motion } from "framer-motion";

const EXAMPLES = [
  "Do autonomous coding agents measurably improve software engineering productivity without increasing defect rates?",
  "Is intermittent fasting more effective than caloric restriction for long-term metabolic health?",
  "Does psilocybin therapy outperform SSRIs for treatment-resistant depression?",
  "Are carbon offsets a credible mechanism for corporate net-zero claims?",
];

type Props = {
  question: string;
  setQuestion: (v: string) => void;
  threshold: number; // 0..100
  setThreshold: (v: number) => void;
  maxPasses: number;
  setMaxPasses: (v: number) => void;
  isSubmitting: boolean;
  onSubmit: (e: FormEvent<HTMLFormElement>) => void;
};

export function Hero(props: Props) {
  const {
    question,
    setQuestion,
    threshold,
    setThreshold,
    maxPasses,
    setMaxPasses,
    isSubmitting,
    onSubmit,
  } = props;

  const rangeStyle = useMemo(
    () => ({ ["--p" as never]: `${threshold}%` } as React.CSSProperties),
    [threshold]
  );

  return (
    <motion.section
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
      className="relative mx-auto flex w-full max-w-[1080px] flex-col items-center px-4 pt-10 pb-20 text-center sm:pt-16"
    >
      {/* Eyebrow */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.05, duration: 0.5 }}
        className="inline-flex items-center gap-2 rounded-full border border-brass/25 bg-brass/5 px-3.5 py-1.5"
      >
        <span className="live-dot" />
        <span className="text-[10px] font-medium uppercase tracking-[0.32em] text-ember/80">
          Quorum · AI Research Council
        </span>
      </motion.div>

      {/* Headline */}
      <h1 className="mt-7 font-display text-[clamp(3rem,7.5vw,6.5rem)] leading-[0.98] tracking-tight text-ember">
        Don't ask a chatbot.
        <br />
        <span className="italic text-gold-grad">Convene a council.</span>
      </h1>

      <p className="mt-6 max-w-[640px] text-[15px] leading-7 text-slate-400">
        One question. Seven specialized agents — Chair, Scout, Reader, Critic, Synthesizer,
        Gap-Finder, Archivist — autonomously researching with a confidence-gated retry loop.
      </p>

      {/* Composer */}
      <motion.form
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.18, duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
        onSubmit={onSubmit}
        className="surface-raised mt-12 w-full rounded-[28px] p-2 text-left"
      >
        <div className="rounded-[22px] bg-abyss/60 p-5 sm:p-7">
          <div className="flex items-center gap-2 pb-3">
            <span className="eyebrow">Inquiry</span>
            <div className="h-px flex-1 bg-gradient-to-r from-brass/25 to-transparent" />
          </div>

          <textarea
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            rows={3}
            placeholder="Pose a research question to the council…"
            className="w-full resize-none border-0 bg-transparent p-0 font-display text-[clamp(1.4rem,2.2vw,2rem)] leading-snug text-ember outline-none placeholder:text-slate-600 focus:ring-0"
            spellCheck={false}
          />

          {/* Controls */}
          <div className="mt-6 grid gap-5 border-t border-brass/10 pt-5 sm:grid-cols-[1fr_1fr_auto] sm:items-end">
            {/* Threshold */}
            <div>
              <div className="flex items-center justify-between">
                <label className="eyebrow">Confidence threshold</label>
                <span className="font-mono text-sm text-ember">{threshold}%</span>
              </div>
              <input
                type="range"
                min={50}
                max={95}
                step={1}
                value={threshold}
                onChange={(e) => setThreshold(parseInt(e.target.value, 10))}
                className="range-gold mt-2"
                style={rangeStyle}
              />
            </div>

            {/* Passes */}
            <div>
              <label className="eyebrow">Max research passes</label>
              <div className="mt-2 inline-flex rounded-xl border border-brass/15 bg-abyss/70 p-1">
                {[1, 2, 3].map((n) => (
                  <button
                    type="button"
                    key={n}
                    onClick={() => setMaxPasses(n)}
                    className={`rounded-lg px-4 py-1.5 text-sm font-medium transition ${
                      maxPasses === n
                        ? "bg-brass/20 text-ember shadow-[inset_0_0_0_1px_rgba(212,164,74,0.3)]"
                        : "text-slate-400 hover:text-ember"
                    }`}
                  >
                    {n}
                  </button>
                ))}
              </div>
            </div>

            <button
              type="submit"
              disabled={isSubmitting || !question.trim()}
              className="btn-gold w-full sm:w-auto"
            >
              {isSubmitting ? (
                <>
                  <Spinner /> Convening…
                </>
              ) : (
                <>
                  Convene Council
                  <span aria-hidden>→</span>
                </>
              )}
            </button>
          </div>
        </div>
      </motion.form>

      {/* Example questions */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.4, duration: 0.6 }}
        className="mt-8 flex w-full flex-col items-start gap-2"
      >
        <p className="eyebrow">Try a question</p>
        <div className="flex w-full flex-wrap gap-2">
          {EXAMPLES.map((q) => (
            <button
              key={q}
              type="button"
              onClick={() => setQuestion(q)}
              className="row-hover max-w-full rounded-full border border-brass/12 bg-white/[0.02] px-3.5 py-1.5 text-left text-[12px] text-slate-400 hover:text-ember"
            >
              <span className="line-clamp-1">{q}</span>
            </button>
          ))}
        </div>
      </motion.div>

      {/* Council preview strip */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.55, duration: 0.7 }}
        className="mt-14 grid w-full grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-7"
      >
        {[
          ["◆", "Chair"],
          ["✦", "Scout"],
          ["❖", "Reader"],
          ["✶", "Critic"],
          ["✷", "Synthesizer"],
          ["◇", "Gap-Finder"],
          ["✧", "Archivist"],
        ].map(([g, n], i) => (
          <motion.div
            key={n}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.6 + i * 0.05, duration: 0.4 }}
            className="surface flex items-center gap-3 rounded-2xl px-3 py-2.5"
          >
            <span className="font-display text-xl text-gold-grad">{g}</span>
            <span className="text-xs font-medium text-slate-300">{n}</span>
          </motion.div>
        ))}
      </motion.div>
    </motion.section>
  );
}

function Spinner() {
  return (
    <span
      className="inline-block h-3.5 w-3.5 animate-spin rounded-full border-2 border-current border-r-transparent"
      aria-hidden
    />
  );
}
