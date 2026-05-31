"use client";

import { BookOpen } from "lucide-react";

/**
 * One plain-language reference for every domain term in the console. The same
 * phrasings are reused as inline tooltips next to each metric, so a first-time
 * user never has to leave the screen to decode a label.
 */
export type GlossaryEntry = { term: string; tip: string };

export const GLOSSARY: GlossaryEntry[] = [
  {
    term: "Impact ratio",
    tip: "A group's pass rate ÷ the best group's pass rate. 1.00 = treated equally; below 0.80 is a red flag.",
  },
  {
    term: "80% rule (EEOC 4/5ths)",
    tip: "The fairness line: if a group passes less than 80% as often as the top group, that counts as unfair.",
  },
  {
    term: "Unfair gap (adverse impact)",
    tip: "A group passes far less often than the top group — the kind of gap regulators treat as discrimination.",
  },
  {
    term: "Transcription bias",
    tip: "The speech-to-text mishears accented voices, so a correct spoken answer gets garbled and fails before it's even graded.",
  },
  {
    term: "Grader bias",
    tip: "The AI judge gives the exact same words a lower score based on a perceived identity, like the candidate's name.",
  },
  {
    term: "Qualified answers",
    tip: "Only the runs where someone actually gave a competent answer — so a genuinely wrong answer never counts as bias.",
  },
  {
    term: "Mishear rate",
    tip: "Word Error Rate — the share of words the speech-to-text got wrong. Higher means the machine mishears that voice more.",
  },
  {
    term: "Tests per group",
    tip: "How many times we replay the answer for each accent / name / gender combination. More tests = steadier numbers.",
  },
  {
    term: "Matched test set",
    tip: "The same competent answer replayed across many accents, names, and genders. Only the identity changes — the answer is identical.",
  },
  {
    term: "Judge accuracy",
    tip: "How often the AI judge's pass/fail matches the known-correct answer key from human experts.",
  },
  {
    term: "Wrongly-failed rate",
    tip: "How often the AI judge fails an answer that actually deserved a pass.",
  },
  {
    term: "Control group (gender)",
    tip: "Gender is the sanity check. If it shows no gap, the test isn't just flagging random noise — so the real findings are trustworthy.",
  },
];

/**
 * A header affordance that opens the full glossary. Uses a native <details>
 * element so it works with keyboard and screen readers with no extra JS.
 */
export function GlossaryButton() {
  return (
    <details className="group relative">
      <summary className="flex cursor-pointer list-none items-center gap-1.5 rounded-md border border-border bg-card px-3 py-1.5 text-xs font-medium text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring [&::-webkit-details-marker]:hidden">
        <BookOpen className="size-3.5" />
        What do these terms mean?
      </summary>
      <div className="absolute right-0 z-50 mt-2 w-[min(22rem,85vw)] rounded-xl border border-border bg-card p-4 text-left shadow-xl">
        <p className="mb-3 text-sm font-semibold text-foreground">
          Plain-language glossary
        </p>
        <dl className="space-y-3">
          {GLOSSARY.map((g) => (
            <div key={g.term}>
              <dt className="text-xs font-semibold text-foreground">{g.term}</dt>
              <dd className="mt-0.5 text-xs leading-relaxed text-muted-foreground">
                {g.tip}
              </dd>
            </div>
          ))}
        </dl>
      </div>
    </details>
  );
}
