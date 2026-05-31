import fs from "fs";
import path from "path";

import Link from "next/link";
import { ArrowLeft } from "lucide-react";

import type { Audit, ScenarioInfo } from "@/lib/api";
import { Dashboard } from "@/components/Dashboard";
import { GlossaryButton } from "@/components/Glossary";

export const dynamic = "force-dynamic";

const BACKEND = process.env.BACKEND_URL || "http://localhost:8000";
const ROOT = path.join(process.cwd(), "..");

async function getJson<T>(endpoint: string): Promise<T | null> {
  try {
    const res = await fetch(`${BACKEND}${endpoint}`, { cache: "no-store" });
    return res.ok ? ((await res.json()) as T) : null;
  } catch {
    return null;
  }
}

// Resilience: if the control-plane is unreachable during SSR, fall back to the
// last audit written to disk so the first paint still shows something real.
function auditFromDisk(): Audit | null {
  try {
    return JSON.parse(
      fs.readFileSync(path.join(ROOT, "reports", "audit.json"), "utf-8"),
    );
  } catch {
    return null;
  }
}

export default async function ConsolePage() {
  const [audit, scenarios] = await Promise.all([
    getJson<Audit>("/api/audit"),
    getJson<ScenarioInfo[]>("/api/scenarios"),
  ]);
  const initialAudit = audit ?? auditFromDisk();

  return (
    <main className="container max-w-[1100px] py-10">
      <header className="mb-8">
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <Link
              href="/"
              className="flex size-9 items-center justify-center rounded-lg bg-primary/15 text-lg font-bold text-primary transition-colors hover:bg-primary/25"
              aria-label="Back to home"
            >
              F
            </Link>
            <h1 className="text-2xl font-bold tracking-tight">FairBench</h1>
          </div>
          <div className="flex items-center gap-3">
            <Link
              href="/"
              className="hidden items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground sm:flex"
            >
              <ArrowLeft className="size-4" />
              Home
            </Link>
            <GlossaryButton />
          </div>
        </div>
        <p className="mt-3 max-w-2xl text-sm leading-relaxed text-muted-foreground">
          Score a spoken conversation on skills, then check the score is{" "}
          <span className="text-foreground">fair</span>. The trick: we give the AI
          the <i>same</i> good answer in many accents and names — so if some
          groups pass less often, that&apos;s the AI being unfair, not the person.
          New here? Open{" "}
          <span className="text-foreground">What do these terms mean?</span> any
          time.
        </p>
      </header>

      <Dashboard
        initialAudit={initialAudit}
        initialScenarios={scenarios ?? []}
      />

      <footer className="mt-12 border-t border-border pt-5 text-xs leading-relaxed text-muted-foreground">
        Built on Pipecat, NVIDIA Nemotron, Gradium, Twilio, and Cekura. Fairness
        is the <span className="text-foreground">evaluator&apos;s</span> fairness,
        not the speaker&apos;s skill: the same competent performance is delivered
        across every demographic variant, so any pass/fail disparity is bias in
        the transcription or the grader — not the person.
      </footer>
    </main>
  );
}
