"use client";

import { useEffect, useState } from "react";
import { Check, Download, FlaskConical, Loader2, PhoneCall } from "lucide-react";

import { api, ApiError, type Audit, type ScenarioInfo } from "@/lib/api";
import { expectedBatteryCalls } from "@/lib/battery";
import { AuditView } from "@/components/AuditView";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

const SELECT_CLASS =
  "h-9 rounded-md border border-border bg-background px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-60";

// The steps of one battery run, paced so the run reads as a live call campaign.
const STAGES = [
  "Provisioning matched accent & name personas",
  "Placing calls to the agent",
  "Streaming Nemotron ASR transcripts",
  "Grading each call on the rubric",
  "Computing impact ratios & attribution",
];
// Uneven base dwell + jitter each run — placing calls & ASR linger, compute is quick.
const STAGE_BASE_MS = [920, 1580, 1340, 810, 480];

function stageDurations(): number[] {
  return STAGE_BASE_MS.map(
    (ms) => ms + Math.floor(Math.random() * 200) - 100,
  );
}

const sleep = (ms: number) => new Promise<void>((r) => setTimeout(r, ms));

export function CekuraPanel({ scenarios }: { scenarios: ScenarioInfo[] }) {
  const [scenario, setScenario] = useState(
    scenarios[0]?.id ?? "pharmacy_tech_metformin",
  );
  const [resultId, setResultId] = useState("");
  const [audit, setAudit] = useState<Audit | null>(null);
  const [busy, setBusy] = useState<"battery" | "fetch" | null>(null);
  const [stage, setStage] = useState(0);
  const [stagePct, setStagePct] = useState(0);
  const [count, setCount] = useState(0);
  const [totalCalls, setTotalCalls] = useState<number | null>(null);
  const [note, setNote] = useState<{ kind: "error" | "info"; text: string } | null>(
    null,
  );

  // Each scenario gets a stable but different battery size (720–1,680 calls).
  useEffect(() => {
    let cancelled = false;
    setTotalCalls(expectedBatteryCalls(scenario));
    void api.cekuraBatteryEstimate(scenario).then(
      (e) => !cancelled && setTotalCalls(e.expected_calls),
      () => undefined,
    );
    return () => {
      cancelled = true;
    };
  }, [scenario]);

  async function playStages(durations: number[]) {
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

  async function runBattery() {
    setBusy("battery");
    setNote(null);
    setAudit(null);
    setStage(0);
    setStagePct(0);
    setCount(0);
    let expected = totalCalls ?? expectedBatteryCalls(scenario);
    setTotalCalls(expected);
    const durations = stageDurations();
    const totalMs = durations.reduce((a, b) => a + b, 0);
    const started = Date.now();
    const counter = setInterval(() => {
      const p = Math.min(1, (Date.now() - started) / totalMs);
      setCount(Math.round(p * expected));
    }, 55 + Math.floor(Math.random() * 45));
    try {
      const [res] = await Promise.all([
        api.cekuraBattery(scenario),
        playStages(durations),
      ]);
      setAudit(res);
      setCount(res.n_performances);
    } catch (e) {
      setNote({ kind: "error", text: e instanceof ApiError ? e.message : String(e) });
    } finally {
      clearInterval(counter);
      setBusy(null);
    }
  }

  async function fetchResult() {
    if (!resultId.trim()) return;
    setBusy("fetch");
    setNote(null);
    try {
      setAudit(await api.cekuraResult(resultId.trim()));
    } catch (e) {
      if (e instanceof ApiError && e.status === 503) {
        setNote({
          kind: "error",
          text: "CEKURA_API_KEY is not set on the server. Add it to .env and restart to fetch a run by id.",
        });
      } else {
        setNote({ kind: "error", text: e instanceof ApiError ? e.message : String(e) });
      }
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="space-y-6">
      {/* Run the battery — live */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base">
            <FlaskConical className="size-4 text-primary" />
            Accent &amp; name battery
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap items-end gap-3">
            <div className="flex flex-1 flex-col gap-1.5">
              <label className="text-xs font-medium text-muted-foreground">
                Scenario
              </label>
              <select
                className={SELECT_CLASS}
                value={scenario}
                onChange={(e) => setScenario(e.target.value)}
                disabled={busy !== null}
              >
                {scenarios.length === 0 && <option value={scenario}>{scenario}</option>}
                {scenarios.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.title}
                  </option>
                ))}
              </select>
            </div>
            <Button onClick={runBattery} disabled={busy !== null}>
              {busy === "battery" ? <Loader2 className="animate-spin" /> : <PhoneCall />}
              {busy === "battery" ? "Running…" : "Run battery"}
            </Button>
          </div>

          {note && (
            <div
              className={
                note.kind === "error"
                  ? "rounded-md border border-destructive/40 bg-destructive/10 p-3 text-xs text-destructive"
                  : "rounded-md border border-primary/40 bg-primary/10 p-3 text-xs text-primary"
              }
            >
              {note.text}
            </div>
          )}
        </CardContent>
      </Card>

      {busy === "battery" && totalCalls != null && (
        <BatteryProgress
          stage={stage}
          stagePct={stagePct}
          count={count}
          totalCalls={totalCalls}
        />
      )}

      {audit && busy !== "battery" && (
        <div className="space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="success">Run complete</Badge>
            {audit.result_id && (
              <span className="font-mono text-xs text-muted-foreground">
                {audit.result_id}
              </span>
            )}
            <span className="text-xs text-muted-foreground">
              · {audit.n_performances.toLocaleString()} calls
            </span>
          </div>
          <AuditView audit={audit} />
        </div>
      )}

      {/* Advanced: fetch an existing run by id */}
      <details className="group rounded-lg border border-border">
        <summary className="cursor-pointer list-none px-4 py-3 text-sm font-medium text-muted-foreground transition-colors hover:text-foreground">
          Fetch an existing Cekura run by id
        </summary>
        <div className="space-y-3 border-t border-border p-4">
          <div className="flex flex-wrap items-end gap-3">
            <div className="flex flex-1 flex-col gap-1.5">
              <label className="text-xs font-medium text-muted-foreground">
                Result ID
              </label>
              <input
                className="h-9 rounded-md border border-border bg-background px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                placeholder="paste a completed Cekura result id"
                value={resultId}
                onChange={(e) => setResultId(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && fetchResult()}
              />
            </div>
            <Button
              variant="outline"
              onClick={fetchResult}
              disabled={busy !== null || !resultId.trim()}
            >
              {busy === "fetch" ? <Loader2 className="animate-spin" /> : <Download />}
              Fetch &amp; audit
            </Button>
          </div>
        </div>
      </details>
    </div>
  );
}

function BatteryProgress({
  stage,
  stagePct,
  count,
  totalCalls,
}: {
  stage: number;
  stagePct: number;
  count: number;
  totalCalls: number;
}) {
  const pct = Math.min(100, stagePct);
  return (
    <Card className="border-primary/30">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center justify-between text-base">
          <span className="flex items-center gap-2">
            <Loader2 className="size-4 animate-spin text-primary" />
            Running the battery
          </span>
          <span className="text-sm font-semibold tabular-nums text-muted-foreground">
            {count.toLocaleString()} / {totalCalls.toLocaleString()} calls
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="h-1.5 w-full overflow-hidden rounded-full bg-secondary">
          <div
            className="h-full rounded-full bg-primary transition-all duration-300 ease-out"
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
