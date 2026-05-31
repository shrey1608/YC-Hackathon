import {
  AlertTriangle,
  CheckCircle2,
  Mic,
  Scale,
  ShieldCheck,
} from "lucide-react";

import type { Audit, GroupStat } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { InfoTip } from "@/components/ui/info-tip";
import { cn } from "@/lib/utils";

type Tone = "danger" | "warn" | "ok" | "info";

const THRESHOLD = 0.8; // EEOC 4/5ths rule — below this is an unfair gap.

function pct(x: number | null | undefined): string {
  return x == null ? "—" : `${(x * 100).toFixed(1)}%`;
}

function prettyScenario(id?: string): string | null {
  if (!id) return null;
  return id.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function irTone(s: GroupStat): Tone {
  if (s.adverse_impact) return "danger";
  if ((s.impact_ratio ?? 1) < 0.9) return "warn";
  return "ok";
}

const BAR_COLOR: Record<Tone, string> = {
  danger: "bg-destructive",
  warn: "bg-warning",
  ok: "bg-success",
  info: "bg-primary",
};

/** A horizontal bar with an optional reference line (e.g. the 0.80 fairness line). */
function Bar({
  value,
  tone,
  threshold,
  ariaLabel,
}: {
  value: number;
  tone: Tone;
  threshold?: number | null;
  ariaLabel?: string;
}) {
  return (
    <div
      className="relative h-2.5 w-28 overflow-hidden rounded-full bg-secondary"
      role="img"
      aria-label={ariaLabel}
    >
      <div
        className={cn("h-full rounded-full", BAR_COLOR[tone])}
        style={{ width: `${Math.max(2, Math.min(100, value * 100))}%` }}
      />
      {threshold != null && (
        <span
          className="absolute inset-y-0 w-0.5 bg-foreground/70"
          style={{ left: `${threshold * 100}%` }}
          aria-hidden
        />
      )}
    </div>
  );
}

function flaggedGroups(audit: Audit, attr: string): string[] {
  return Object.entries(audit.fairness[attr] ?? {})
    .filter(([, s]) => s.adverse_impact)
    .map(([g]) => g);
}

type Finding = { tone: Tone; icon: React.ReactNode; title: string; body: string };

/**
 * The core of the product: translate the numbers into *why* a gap exists — the
 * speech-to-text mishearing accents vs. the AI judge under-crediting names —
 * plus a clean control axis that proves the test isn't just flagging noise.
 */
function deriveFindings(audit: Audit): Finding[] {
  const accent = flaggedGroups(audit, "accent");
  const name = flaggedGroups(audit, "name_origin");
  const gender = flaggedGroups(audit, "gender");
  const asr = audit.asr_bias.map((a) => a.group);
  const findings: Finding[] = [];

  if (accent.length && asr.length) {
    findings.push({
      tone: "warn",
      icon: <Mic className="size-4" />,
      title: "Transcription bias — the machine mishears",
      body: `The speech-to-text mishears ${accent.join(", ")} speakers (their words are misheard the most), so the same good answer fails more often. The fix is better transcription, not a stricter checklist.`,
    });
  } else if (accent.length) {
    findings.push({
      tone: "danger",
      icon: <Scale className="size-4" />,
      title: "Accent penalized by the judge",
      body: `${accent.join(", ")} speakers fail more often even though their words are transcribed just as accurately. The judge is penalizing the accent itself, not the answer.`,
    });
  }
  if (name.length) {
    findings.push({
      tone: "danger",
      icon: <Scale className="size-4" />,
      title: "Grader bias — the judge under-credits",
      body: `People with ${name.join(", ")} names fail more often even though their transcripts are just as accurate. Same good answer, different verdict — the judge is reacting to the name, not the performance.`,
    });
  }
  if (gender.length) {
    findings.push({
      tone: "warn",
      icon: <AlertTriangle className="size-4" />,
      title: "Heads up: the control group moved",
      body: "Gender is the sanity check and it shouldn't show a gap. Because it did, the test may be noisy — read the findings above with extra caution.",
    });
  } else {
    findings.push({
      tone: "ok",
      icon: <ShieldCheck className="size-4" />,
      title: "Control group is clean",
      body: "Gender is the sanity check and shows no gap, so the test isn't crying wolf. That makes the findings above trustworthy.",
    });
  }
  return findings;
}

const FINDING_STYLES: Record<Tone, string> = {
  danger: "border-destructive/40 bg-destructive/5",
  warn: "border-warning/40 bg-warning/5",
  ok: "border-success/40 bg-success/5",
  info: "border-primary/40 bg-primary/5",
};

const FINDING_ICON: Record<Tone, string> = {
  danger: "bg-destructive/15 text-destructive",
  warn: "bg-warning/15 text-warning",
  ok: "bg-success/15 text-success",
  info: "bg-primary/15 text-primary",
};

const STAT_TONE: Record<Tone, string> = {
  danger: "text-destructive",
  warn: "text-warning",
  ok: "text-success",
  info: "text-foreground",
};

function Stat({
  label,
  value,
  caption,
  tone = "info",
  tip,
}: {
  label: string;
  value: React.ReactNode;
  caption?: string;
  tone?: Tone;
  tip?: React.ReactNode;
}) {
  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-center gap-1 text-[0.7rem] font-medium uppercase tracking-wider text-muted-foreground">
          {label}
          {tip && <InfoTip align="start">{tip}</InfoTip>}
        </div>
        <div className={cn("mt-1 text-2xl font-bold tabular-nums", STAT_TONE[tone])}>
          {value}
        </div>
        {caption && (
          <div className="mt-0.5 text-xs leading-snug text-muted-foreground">
            {caption}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export function AuditView({ audit }: { audit: Audit }) {
  const ok = audit.verdict.startsWith("PASS");
  const rel = audit.reliability;
  const findings = deriveFindings(audit);
  const scenarioLabel = prettyScenario(audit.scenario);
  const sourceLabel =
    audit.source === "cekura"
      ? "Cekura"
      : audit.source === "matched_battery"
        ? "matched battery"
        : audit.source
          ? audit.source
          : null;

  const agreement = rel.agreement;
  const falseFail = rel.false_fail_rate;

  return (
    <div className="space-y-6">
      {/* Verdict — plain-language takeaway, raw status kept as a small tag */}
      <div
        className={cn(
          "flex flex-wrap items-center gap-3 rounded-lg border p-4",
          ok
            ? "border-success/40 bg-success/10"
            : "border-destructive/40 bg-destructive/10",
        )}
      >
        {ok ? (
          <CheckCircle2 className="size-6 shrink-0 text-success" />
        ) : (
          <AlertTriangle className="size-6 shrink-0 text-destructive" />
        )}
        <div>
          <div
            className={cn(
              "text-lg font-bold leading-tight",
              ok ? "text-success" : "text-destructive",
            )}
          >
            {ok ? "Graded fairly" : "Not fair to ship yet"}
          </div>
          <div className="text-xs leading-relaxed text-muted-foreground">
            {ok
              ? "Among people who gave a good answer, every group passed at a similar rate — all above the 80% fairness line."
              : "Some groups get a worse grade for the exact same good answer, and at least one passes below the 80% fairness line. Fix before deploying."}
          </div>
        </div>
        <div className="ml-auto flex items-center gap-2">
          {scenarioLabel && <Badge variant="outline">{scenarioLabel}</Badge>}
          {sourceLabel ? (
            <Badge variant={audit.source === "cekura" ? "success" : "secondary"}>
              {sourceLabel}
            </Badge>
          ) : (
            <Badge variant="secondary">simulated</Badge>
          )}
        </div>
      </div>

      {/* Attribution — the differentiator */}
      {findings.length > 0 && (
        <div>
          <div className="mb-3">
            <h3 className="text-sm font-semibold text-foreground">
              What&apos;s causing the gap?
            </h3>
            <p className="text-xs text-muted-foreground">
              We separate the machine mishearing accents (speech-to-text) from the
              AI judge reacting to names (the grader) — so you fix the right thing.
            </p>
          </div>
          <div className="grid gap-3 md:grid-cols-3">
            {findings.map((f) => (
              <div
                key={f.title}
                className={cn("rounded-lg border p-4", FINDING_STYLES[f.tone])}
              >
                <div className="flex items-center gap-2">
                  <span
                    className={cn(
                      "flex size-7 items-center justify-center rounded-md",
                      FINDING_ICON[f.tone],
                    )}
                  >
                    {f.icon}
                  </span>
                  <span className="text-sm font-semibold">{f.title}</span>
                </div>
                <p className="mt-2 text-xs leading-relaxed text-muted-foreground">
                  {f.body}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Summary stats */}
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Stat
          label="Answers graded"
          value={audit.n_performances}
          caption="across all groups"
        />
        <Stat
          label="Qualified answers"
          value={
            audit.fairness_cohort_n != null
              ? `${audit.fairness_cohort_n} of ${audit.n_performances}`
              : "—"
          }
          caption="gave a competent answer"
          tip="Only the runs where someone actually gave a competent answer. Fairness is measured on these, so a genuinely wrong answer never counts as bias."
        />
        <Stat
          label="Judge accuracy"
          value={pct(agreement)}
          caption="matches the answer key"
          tone={agreement == null ? "info" : agreement >= 0.8 ? "ok" : "warn"}
          tip="How often the AI judge's pass/fail matches the known-correct answer key from human experts. Higher is better."
        />
        <Stat
          label="Wrongly failed"
          value={pct(falseFail)}
          caption="good answers the judge failed"
          tone={falseFail == null ? "info" : falseFail <= 0.1 ? "ok" : "warn"}
          tip="How often the judge fails an answer that actually deserved a pass. Lower is better."
        />
      </div>

      {/* Legend for the fairness bars */}
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 rounded-lg border border-dashed border-border px-4 py-2.5 text-xs text-muted-foreground">
        <span className="flex items-center gap-1.5">
          <span className="h-2.5 w-6 rounded-full bg-success" /> at/above 0.80
        </span>
        <span className="flex items-center gap-1.5">
          <span className="h-2.5 w-6 rounded-full bg-warning" /> close (watch)
        </span>
        <span className="flex items-center gap-1.5">
          <span className="h-2.5 w-6 rounded-full bg-destructive" /> below 0.80
          (flagged)
        </span>
        <span className="flex items-center gap-1.5">
          <span className="inline-block h-3 w-0.5 bg-foreground/70" /> the 0.80
          fairness line
        </span>
      </div>

      {/* Fairness tables */}
      {Object.entries(audit.fairness).map(([attr, groups]) => {
        const flagged = Object.values(groups).filter((s) => s.adverse_impact).length;
        const best = Math.max(...Object.values(groups).map((s) => s.pass_rate));
        return (
          <Card key={attr}>
            <CardHeader className="pb-3">
              <CardTitle className="flex flex-wrap items-center gap-2 text-base">
                <span className="flex items-center gap-1">
                  Fairness by {attr.replace(/_/g, " ")}
                  <InfoTip align="start">
                    {attr === "accent"
                      ? "Does each accent pass at a similar rate? A low number here often means the speech-to-text is mishearing that accent."
                      : attr === "name_origin"
                        ? "Does each name origin pass at a similar rate? A low number here with clean transcription points to the AI judge."
                        : "Gender is the control group — it should stay flat. If it moves, the test may be noisy."}
                  </InfoTip>
                </span>
                {flagged > 0 ? (
                  <Badge variant="destructive">
                    {flagged} group{flagged > 1 ? "s" : ""} flagged
                  </Badge>
                ) : (
                  <Badge variant="success">all clear</Badge>
                )}
              </CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-y border-border bg-secondary/40 text-[0.7rem] uppercase tracking-wider text-muted-foreground">
                    <th scope="col" className="px-5 py-2 text-left font-semibold">
                      Group
                    </th>
                    <th scope="col" className="px-5 py-2 text-left font-semibold">
                      Pass rate
                    </th>
                    <th scope="col" className="px-5 py-2 text-left font-semibold">
                      <span className="flex items-center gap-1">
                        Fairness ratio
                        <InfoTip>
                          This group&apos;s pass rate ÷ the top group&apos;s pass
                          rate. 1.00 = treated equally; below 0.80 fails the EEOC
                          80% rule.
                        </InfoTip>
                      </span>
                    </th>
                    <th scope="col" className="px-5 py-2 text-left font-semibold">
                      Answers
                    </th>
                    <th scope="col" className="px-5 py-2 text-left font-semibold">
                      Status
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {Object.entries(groups)
                    .sort((a, b) => (a[1].impact_ratio ?? 1) - (b[1].impact_ratio ?? 1))
                    .map(([g, s]) => {
                      const isBaseline = s.pass_rate === best;
                      return (
                        <tr key={g}>
                          <td className="px-5 py-2.5 font-medium">
                            <span className="flex items-center gap-2">
                              {g.replace(/_/g, " ")}
                              {isBaseline && (
                                <span className="rounded bg-secondary px-1.5 py-0.5 text-[0.65rem] font-normal uppercase tracking-wide text-muted-foreground">
                                  baseline
                                </span>
                              )}
                            </span>
                          </td>
                          <td className="px-5 py-2.5 tabular-nums">
                            {pct(s.pass_rate)}
                          </td>
                          <td className="px-5 py-2.5">
                            <div className="flex items-center gap-2">
                              <Bar
                                value={s.impact_ratio ?? 1}
                                tone={irTone(s)}
                                threshold={THRESHOLD}
                                ariaLabel={`Fairness ratio ${
                                  s.impact_ratio?.toFixed(2) ?? "n/a"
                                }${s.adverse_impact ? ", below 0.80 — flagged" : ""}`}
                              />
                              <span className="tabular-nums text-xs text-muted-foreground">
                                {s.impact_ratio == null
                                  ? "—"
                                  : s.impact_ratio.toFixed(2)}
                              </span>
                            </div>
                          </td>
                          <td className="px-5 py-2.5 tabular-nums text-muted-foreground">
                            {s.n}
                          </td>
                          <td className="px-5 py-2.5">
                            {s.adverse_impact ? (
                              <Badge variant="destructive">unfair gap</Badge>
                            ) : irTone(s) === "warn" ? (
                              <span className="text-xs text-warning">watch</span>
                            ) : (
                              <span className="text-xs text-success">ok</span>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                </tbody>
              </table>
            </CardContent>
          </Card>
        );
      })}

      {/* Transcription (ASR) bias */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex flex-wrap items-center gap-2 text-base">
            <Mic className="size-4 text-muted-foreground" />
            <span className="flex items-center gap-1">
              Which voices get misheard
              <InfoTip align="start">
                Mishear rate (Word Error Rate) = the share of words the
                speech-to-text got wrong. A high rate here explains accent gaps
                above — the machine, not the answer.
              </InfoTip>
            </span>
          </CardTitle>
        </CardHeader>
        <CardContent className={audit.asr_bias.length === 0 ? "" : "p-0"}>
          {audit.asr_bias.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No mishearing gap found — so any accent gap above is the judge, not
              the transcription.
            </p>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-y border-border bg-secondary/40 text-[0.7rem] uppercase tracking-wider text-muted-foreground">
                  <th scope="col" className="px-5 py-2 text-left font-semibold">
                    Accent
                  </th>
                  <th scope="col" className="px-5 py-2 text-left font-semibold">
                    Mishear rate
                  </th>
                  <th scope="col" className="px-5 py-2 text-left font-semibold">
                    Extra errors vs best
                  </th>
                  <th scope="col" className="px-5 py-2 text-left font-semibold">
                    <span className="sr-only">Distribution</span>
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {audit.asr_bias.map((a) => (
                  <tr key={a.group}>
                    <td className="px-5 py-2.5 font-medium">
                      {a.group.replace(/_/g, " ")}
                    </td>
                    <td className="px-5 py-2.5 tabular-nums">
                      {(a.avg_wer * 100).toFixed(1)}%
                    </td>
                    <td
                      className={cn(
                        "px-5 py-2.5 tabular-nums",
                        a.gap_vs_best >= 0.05 ? "text-warning" : "text-muted-foreground",
                      )}
                    >
                      +{(a.gap_vs_best * 100).toFixed(1)}%
                    </td>
                    <td className="px-5 py-2.5">
                      <Bar
                        value={Math.min(1, a.avg_wer / 0.3)}
                        tone="warn"
                        ariaLabel={`Mishear rate ${(a.avg_wer * 100).toFixed(1)} percent`}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
