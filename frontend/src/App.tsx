import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { AnimatePresence } from "framer-motion";
import { createQuery, getQueryResult, getQueryStatus } from "./api";
import { QueryStatus, VerdictPayload } from "./types";
import { Hero } from "./components/Hero";
import { Council } from "./components/Council";
import { Verdict } from "./components/Verdict";
import { Explorer } from "./components/Explorer";

type Phase = "compose" | "running" | "verdict";

function App() {
  const [question, setQuestion] = useState(
    "Do autonomous coding agents measurably improve software engineering productivity without increasing defect rates?"
  );
  const [threshold, setThreshold] = useState(74);
  const [maxPasses, setMaxPasses] = useState(2);

  const [queryId, setQueryId] = useState<string | null>(null);
  const [status, setStatus] = useState<QueryStatus | null>(null);
  const [result, setResult] = useState<VerdictPayload | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const intervalRef = useRef<ReturnType<typeof window.setInterval> | null>(null);
  const explorerRef = useRef<HTMLDivElement | null>(null);
  // Track whether we're in a reset state to prevent stale poll from setting result
  const resetCounterRef = useRef(0);

  const stopPolling = useCallback(() => {
    if (intervalRef.current !== null) {
      window.clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  }, []);

  useEffect(() => {
    if (!queryId) return;
    let active = true;
    let done = false;
    const capturedCounter = resetCounterRef.current;

    const poll = async () => {
      if (done || !active) return;
      // Bail if a reset happened since this poll started
      if (resetCounterRef.current !== capturedCounter) return;
      try {
        const s = await getQueryStatus(queryId);
        if (!active || resetCounterRef.current !== capturedCounter) return;
        setStatus(s);
        if (s.status === "completed" || s.status === "failed") {
          done = true;
          stopPolling();
          const r = await getQueryResult(queryId);
          if (!active || resetCounterRef.current !== capturedCounter) return;
          setError(r.error_message ?? null);
          setResult(r.result);
        }
      } catch (e) {
        if (active && resetCounterRef.current === capturedCounter) {
          setError(e instanceof Error ? e.message : "Polling failed.");
        }
      }
    };

    void poll();
    intervalRef.current = window.setInterval(() => void poll(), 1800);
    return () => {
      active = false;
      done = true;
      stopPolling();
    };
  }, [queryId, stopPolling]);

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    stopPolling();
    setIsSubmitting(true);
    setError(null);
    setResult(null);
    setStatus(null);
    setQueryId(null);
    try {
      const created = await createQuery({
        question,
        confidence_threshold: threshold / 100,
        max_passes: maxPasses,
      });
      setQueryId(created.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start research.");
    } finally {
      setIsSubmitting(false);
    }
  }

  function handleReset() {
    // Increment counter so any in-flight poll ignores its result
    resetCounterRef.current += 1;
    stopPolling();
    setQueryId(null);
    setStatus(null);
    setResult(null);
    setError(null);
    setIsSubmitting(false);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function handleExplore() {
    explorerRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  // Phase
  const phase: Phase = result
    ? "verdict"
    : queryId || isSubmitting
    ? "running"
    : "compose";

  return (
    <div className="relative min-h-screen overflow-x-hidden text-slate-100">
      {/* Ambient layers */}
      <div className="pointer-events-none fixed inset-0">
        <div className="ambient-grid absolute inset-0" />
        <div className="absolute -top-40 left-1/2 h-[720px] w-[720px] -translate-x-1/2 rounded-full bg-brass/[0.06] blur-[160px]" />
        <div className="absolute top-[30%] -right-64 h-[520px] w-[520px] rounded-full bg-blue-900/[0.08] blur-[140px]" />
        <div className="absolute bottom-[10%] -left-32 h-[420px] w-[420px] rounded-full bg-indigo-900/[0.06] blur-[120px]" />
      </div>

      {/* Top nav */}
      <header className="relative z-10 mx-auto flex max-w-[1280px] items-center justify-between px-4 py-5 sm:px-6">
        <div className="flex items-center gap-2.5">
          <div className="grid h-8 w-8 place-items-center rounded-lg border border-brass/30 bg-brass/10 font-display text-lg text-gold-grad">
            Q
          </div>
          <span className="font-display text-xl tracking-tight text-ember">Quorum</span>
        </div>
        <nav className="flex items-center gap-2">
          {phase !== "compose" && (
            <button
              onClick={handleReset}
              className="btn-ghost"
              key="new-inquiry-btn"
            >
              <span aria-hidden>↺</span> New inquiry
            </button>
          )}
          <a
            href="https://github.com"
            target="_blank"
            rel="noreferrer"
            className="hidden text-xs text-slate-500 hover:text-ember sm:inline"
          >
            v0.5 · cinematic
          </a>
        </nav>
      </header>

      {/* Error banner */}
      {error && (
        <div className="relative z-10 mx-auto mb-4 max-w-[1280px] px-4 sm:px-6">
          <div className="surface flex items-center gap-3 rounded-2xl border-rose-500/30 bg-rose-500/5 px-4 py-3 text-sm text-rose-200">
            <span>⚠</span>
            <span className="flex-1">{error}</span>
            <button onClick={() => setError(null)} className="text-xs text-rose-300 hover:underline">
              dismiss
            </button>
          </div>
        </div>
      )}

      {/* Simulated banner */}
      {(result?.simulated_research || status?.simulated_research) && (
        <div className="relative z-10 mx-auto mb-2 max-w-[1280px] px-4 sm:px-6">
          <div className="surface flex items-center gap-3 rounded-2xl border-amber-500/30 bg-amber-500/[0.06] px-4 py-3 text-xs text-amber-200">
            <span>⚠</span>
            <span>
              Using <strong>simulated</strong> literature — Semantic Scholar / arXiv / CrossRef
              were unreachable. These are not real citations.
            </span>
          </div>
        </div>
      )}

      {/* Main content */}
      <main className="relative z-10">
        <AnimatePresence mode="wait">
          {phase === "compose" && (
            <Hero
              key="hero"
              question={question}
              setQuestion={setQuestion}
              threshold={threshold}
              setThreshold={setThreshold}
              maxPasses={maxPasses}
              setMaxPasses={setMaxPasses}
              isSubmitting={isSubmitting}
              onSubmit={handleSubmit}
            />
          )}

          {phase === "running" && (
            <Council
              key="council"
              question={question}
              status={status}
              threshold={(status?.confidence_threshold ?? threshold / 100) as number}
            />
          )}

          {phase === "verdict" && result && (
            <div key="verdict">
              <Verdict
                question={question}
                result={result}
                status={status}
                onReset={handleReset}
                onExplore={handleExplore}
              />
              <Explorer ref={explorerRef} result={result} status={status} />
            </div>
          )}
        </AnimatePresence>
      </main>

      <footer className="relative z-10 mx-auto max-w-[1280px] px-4 pb-8 pt-2 text-center text-[11px] uppercase tracking-[0.28em] text-slate-600 sm:px-6">
        Quorum · An AI Research Council
      </footer>
    </div>
  );
}

export default App;
