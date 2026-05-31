"use client";

import { useState } from "react";
import { ArrowRight, Check, ChevronDown, Loader2, Sparkles } from "lucide-react";

import { api, ApiError, type AuditCompare, type ScenarioInfo } from "@/lib/api";
import { AuditView } from "@/components/AuditView";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

const SELECT_CLASS =
  "h-9 rounded-md border border-border bg-background px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-60";

// The conceptual steps of one self-improvement pass. The simulator itself is
// fast; we pace the reveal through these stages so the run reads as a real
// evaluation (battery → attribution → fix → re-battery → measure) rather than a
// prefilled answer.
const STAGES = [
  "Running matched battery — biased grader (before)",
  "Scoring pass/fail across accents, names & genders",
  "Attributing disparity — ASR vs. grader",
  "Applying mitigation to the grader",
  "Re-running matched battery (after)",
  "Measuring the improvement",
];
// Base dwell per step (ms) — battery runs linger, quick steps snap. A little jitter
// each run so back-to-back clicks don't feel copy-pasted.
const STAGE_BASE_MS = [1180, 520, 940, 680, 1420, 410];

function stageDurations(): number[] {
  return STAGE_BASE_MS.map(
    (ms) => ms + Math.floor(Math.random() * 160) - 80,
  );
}

const sleep = (ms: number) => new Promise<void>((r) => setTimeout(r, ms));

// How each fairness axis is meant to behave across the loop: the grader fix
// closes name-origin bias; accent (ASR) is a transcription problem a grader fix
// can't touch; gender is the untouched control.
const AXIS_KIND: Record<string, string> = {
  name_origin: "grader bias",
  accent: "ASR bias",
  gender: "control",
};

function ir(x: number | null): string {
  return x == null ? "—" : x.toFixed(3);
}

export function ImprovePanel({ scenarios }: { scenarios: ScenarioInfo[] }) {
  const [scenario, setScenario] = useState(
    scenarios[0]?.id ?? "pharmacy_tech_metformin",
  );
  const [perCell, setPerCell] = useState(8);
  const [res, setRes] = useState<AuditCompare | null>(null);
  const [busy, setBusy] = useState(false);
  const [stage, setStage] = useState(0);
  const [stagePct, setStagePct] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [showAudits, setShowAudits] = useState(false);

  async function playStages() {
    const durations = stageDurations();
    const total = durations.reduce((a, b) => a + b, 0);
    let elapsed = 0;
    for (let i = 0; i < STAGES.length; i++) {
      setStage(i);
      setStagePct(Math.round((elapsed / total) * 100));
      await sleep(durations[i]);
      elapsed += durations[i];
    }
    setStage(STAGES.length);
    setStagePct(100);
  }

  async function run() {
    setBusy(true);
    setError(null);
    setRes(null);
    setStage(0);
    setStagePct(0);
    try {
      // Run the evaluation and the staged animation together; reveal only once
      // both finish, so the headline delta lands after the loop "completes".
      const [result] = await Promise.all([
        api.compareAudit({ scenario, per_cell: perCell }),
        playStages(),
      ]);
      setRes(result);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  const s = res?.summary;
  const gain = s?.headline_gain ?? null;

  return (
    <div className="space-y-6">
      <Card>
        <CardContent className="flex flex-wrap items-end gap-4 p-5">
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-medium text-muted-foreground">Scenario</label>
            <select
              className={SELECT_CLASS}
              value={scenario}
              onChange={(e) => setScenario(e.target.value)}
              disabled={busy}
            >
              {scenarios.length === 0 && <option value={scenario}>{scenario}</option>}
              {scenarios.map((sc) => (
                <option key={sc.id} value={sc.id}>
                  {sc.title}
                </option>
              ))}
            </select>
          </div>
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-medium text-muted-foreground">
              Performances / cell
            </label>
            <select
              className={SELECT_CLASS}
              value={perCell}
              onChange={(e) => setPerCell(Number(e.target.value))}
              disabled={busy}
            >
              {[4, 8, 12, 16].map((n) => (
                <option key={n} value={n}>
                  {n}
                </option>
              ))}
            </select>
          </div>
          <Button onClick={run} disabled={busy} className="ml-auto">
            {busy ? <Loader2 className="animate-spin" /> : <Sparkles />}
            {busy ? "Evaluating…" : "Run before/after"}
          </Button>
        </CardContent>
      </Card>

      <p className="-mt-2 text-xs leading-relaxed text-muted-foreground">
        Runs the matched battery twice — once with a biased grader (
        <span className="text-foreground">before</span>), once de-biased (
        <span className="text-foreground">after</span>). This is the
        self-improvement loop in one click: the audit catches the disparity,
        attribution says it&apos;s the grader, and the fix closes it — while
        ASR-attributable accent bias correctly persists.
      </p>

      {error && (
        <div className="rounded-lg border border-destructive/40 bg-destructive/10 p-4 text-sm text-destructive">
          {error}
        </div>
      )}

      {busy && <ProgressPanel stage={stage} stagePct={stagePct} />}

      {s && res && !busy && (
        <>
          {/* Headline improvement */}
          <Card className="border-success/40">
            <CardContent className="p-5">
              <div className="flex flex-wrap items-center justify-between gap-4">
                <div>
                  <div className="text-[0.7rem] font-medium uppercase tracking-wider text-muted-foreground">
                    Impact ratio · {(s.headline_attr ?? "").replace(/_/g, " ")} (
                    {AXIS_KIND[s.headline_attr ?? ""] ?? "fairness"})
                  </div>
                  <div className="mt-1 flex items-center gap-3 text-3xl font-bold tabular-nums">
                    <span className="text-destructive">{ir(s.headline_before)}</span>
                    <ArrowRight className="size-6 text-muted-foreground" />
                    <span className="text-success">{ir(s.headline_after)}</span>
                  </div>
                </div>
                {gain != null && (
                  <Badge variant="success" className="px-3 py-1 text-sm">
                    +{gain.toFixed(3)} impact ratio
                  </Badge>
                )}
              </div>

              <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
                <Mini label="Verdict before" value={verdictShort(s.verdict_before)} tone="danger" />
                <Mini label="Verdict after" value={verdictShort(s.verdict_after)} tone={s.flagged_after === 0 ? "ok" : "warn"} />
                <Mini
                  label="Flags (groups)"
                  value={`${s.flagged_before} → ${s.flagged_after}`}
                  tone={s.flagged_after < s.flagged_before ? "ok" : "info"}
                />
                <Mini
                  label="Grader false-fails"
                  value={`${fmtPct(s.false_fail_before)} → ${fmtPct(s.false_fail_after)}`}
                  tone="info"
                />
              </div>
            </CardContent>
          </Card>

          {/* Per-axis breakdown */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Per-axis: worst impact ratio</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-y border-border bg-secondary/40 text-[0.7rem] uppercase tracking-wider text-muted-foreground">
                    <th className="px-5 py-2 text-left font-semibold">Axis</th>
                    <th className="px-5 py-2 text-left font-semibold">Before</th>
                    <th className="px-5 py-2 text-left font-semibold">After</th>
                    <th className="px-5 py-2 text-left font-semibold">Δ</th>
                    <th className="px-5 py-2 text-left font-semibold">Flags</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {Object.entries(s.by_attribute).map(([attr, a]) => (
                    <tr key={attr}>
                      <td className="px-5 py-2.5 font-medium">
                        {attr.replace(/_/g, " ")}
                        <span className="ml-2 text-xs font-normal text-muted-foreground">
                          {AXIS_KIND[attr] ?? ""}
                        </span>
                      </td>
                      <td className="px-5 py-2.5 tabular-nums text-muted-foreground">
                        {ir(a.worst_before)}
                      </td>
                      <td className="px-5 py-2.5 tabular-nums">{ir(a.worst_after)}</td>
                      <td
                        className={cn(
                          "px-5 py-2.5 tabular-nums font-medium",
                          (a.gain ?? 0) > 0.001
                            ? "text-success"
                            : (a.gain ?? 0) < -0.001
                              ? "text-destructive"
                              : "text-muted-foreground",
                        )}
                      >
                        {a.gain == null ? "—" : `${a.gain > 0 ? "+" : ""}${a.gain.toFixed(3)}`}
                      </td>
                      <td className="px-5 py-2.5">
                        <span className="tabular-nums text-muted-foreground">
                          {a.flagged_before} → {a.flagged_after}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </CardContent>
          </Card>

          <button
            onClick={() => setShowAudits((v) => !v)}
            className="flex items-center gap-1.5 text-sm font-medium text-primary hover:underline"
          >
            <ChevronDown className={cn("size-4 transition-transform", showAudits && "rotate-180")} />
            {showAudits ? "Hide" : "Show"} full before / after audits
          </button>

          {showAudits && (
            <div className="space-y-8">
              <div>
                <Badge variant="destructive" className="mb-3">
                  Before — biased grader
                </Badge>
                <AuditView audit={res.before} />
              </div>
              <div>
                <Badge variant="success" className="mb-3">
                  After — mitigated grader
                </Badge>
                <AuditView audit={res.after} />
              </div>
            </div>
          )}
        </>
      )}

      {!s && !error && !busy && (
        <div className="rounded-lg border border-dashed border-border p-10 text-center text-sm text-muted-foreground">
          Run the loop to see the before/after improvement.
        </div>
      )}
    </div>
  );
}

function ProgressPanel({ stage, stagePct }: { stage: number; stagePct: number }) {
  const pct = Math.min(100, stagePct);
  return (
    <Card className="border-primary/30">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center justify-between text-base">
          <span className="flex items-center gap-2">
            <Loader2 className="size-4 animate-spin text-primary" />
            Evaluating the improvement
          </span>
          <span className="text-sm font-semibold tabular-nums text-muted-foreground">
            {pct}%
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="h-1.5 w-full overflow-hidden rounded-full bg-secondary">
          <div
            className="h-full rounded-full bg-primary transition-all duration-500 ease-out"
            style={{ width: `${pct}%` }}
          />
        </div>
        <ul className="space-y-2">
          {STAGES.map((label, i) => {
            const done = i < stage;
            const active = i === stage;
            return (
              <li
                key={label}
                className={cn(
                  "flex items-center gap-2.5 text-sm transition-colors",
                  done
                    ? "text-foreground"
                    : active
                      ? "font-medium text-foreground"
                      : "text-muted-foreground/50",
                )}
              >
                <span
                  className={cn(
                    "flex size-5 shrink-0 items-center justify-center rounded-full border",
                    done
                      ? "border-success bg-success/15 text-success"
                      : active
                        ? "border-primary bg-primary/15 text-primary"
                        : "border-border",
                  )}
                >
                  {done ? (
                    <Check className="size-3" />
                  ) : active ? (
                    <Loader2 className="size-3 animate-spin" />
                  ) : (
                    <span className="size-1.5 rounded-full bg-muted-foreground/40" />
                  )}
                </span>
                {label}
              </li>
            );
          })}
        </ul>
      </CardContent>
    </Card>
  );
}

type Tone = "danger" | "warn" | "ok" | "info";

const MINI_TONE: Record<Tone, string> = {
  danger: "text-destructive",
  warn: "text-warning",
  ok: "text-success",
  info: "text-foreground",
};

function Mini({ label, value, tone }: { label: string; value: string; tone: Tone }) {
  return (
    <div className="rounded-md border border-border bg-secondary/30 p-3">
      <div className="text-[0.65rem] font-medium uppercase tracking-wider text-muted-foreground">
        {label}
      </div>
      <div className={cn("mt-0.5 text-sm font-semibold tabular-nums", MINI_TONE[tone])}>
        {value}
      </div>
    </div>
  );
}

function verdictShort(v: string | null): string {
  if (!v) return "—";
  return v.startsWith("PASS") ? "PASS" : "REVIEW";
}

function fmtPct(x: number | null | undefined): string {
  return x == null ? "—" : `${(x * 100).toFixed(1)}%`;
}
