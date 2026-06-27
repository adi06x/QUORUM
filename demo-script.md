# QUORUM Demo Script

## 1. Hook
- Open the landing screen and say: "QUORUM is not a chatbot. It's an AI research council."
- Point at the visible pipeline: planning, retrieval, reading, critique, synthesis, verdict.

## 2. Launch a question
- Use this prompt:
  `What does the current academic evidence suggest about retrieval-augmented generation reducing hallucinations in enterprise knowledge tasks?`
- Keep the confidence threshold at `74%`.
- Keep max passes at `2`.

## 3. Narrate the autonomy
- As the timeline updates, call out each agent:
  - Chair decomposes the question.
  - Scout gathers academic sources from Semantic Scholar and arXiv.
  - Reader extracts claims and methods.
  - Critic finds contradictions and gaps.
  - Synthesizer produces a verdict and confidence score.
- If the score lands below threshold, pause and highlight the automatic retry:
  "The chair just launched another pass without me prompting it."

## 4. Show the evidence quality
- Open Evidence Cards and explain that the output is structured, not just a paragraph.
- Open Contradiction Cards and emphasize that QUORUM is designed to challenge its own evidence.

## 5. Show credibility controls
- Scroll to Sources and point out live links.
- If demo mode activates, say:
  "QUORUM never fakes citations. When live research is unavailable, it visibly switches to simulated academic results."

## 6. Close
- End on the Final Verdict panel.
- Summarize:
  "The product demonstrates agent autonomy, evidence retrieval, debate, and confidence-gated retries in a polished interface."

