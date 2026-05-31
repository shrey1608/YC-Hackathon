"use client";

import { useState } from "react";
import { Loader2, Play } from "lucide-react";

import { api, ApiError, type Audit, type ScenarioInfo } from "@/lib/api";
import { AuditView } from "@/components/AuditView";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { InfoTip } from "@/components/ui/info-tip";

const SELECT_CLASS =
  "h-9 rounded-md border border-border bg-background px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring";

export function AuditPanel({
  scenarios,
  initialAudit,
}: {
  scenarios: ScenarioInfo[];
  initialAudit: Audit | null;
}) {
  const [scenario, setScenario] = useState(
    initialAudit?.scenario ?? scenarios[0]?.id ?? "pharmacy_tech_metformin",
  );
  const [perCell, setPerCell] = useState(8);
  const [audit, setAudit] = useState<Audit | null>(initialAudit);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    setBusy(true);
    setError(null);
    try {
      setAudit(await api.runAudit({ scenario, per_cell: perCell }));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardContent className="flex flex-wrap items-end gap-4 p-5">
          <div className="flex flex-col gap-1.5">
            <label htmlFor="audit-scenario" className="text-xs font-medium text-muted-foreground">
              Scenario
            </label>
            <select
              id="audit-scenario"
              className={SELECT_CLASS}
              value={scenario}
              onChange={(e) => setScenario(e.target.value)}
              disabled={busy}
            >
              {scenarios.length === 0 && <option value={scenario}>{scenario}</option>}
              {scenarios.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.title}
                </option>
              ))}
            </select>
          </div>

          <div className="flex flex-col gap-1.5">
            <label htmlFor="audit-percell" className="flex items-center gap-1 text-xs font-medium text-muted-foreground">
              Tests per group
              <InfoTip align="start">
                How many times we replay the answer for each accent / name /
                gender combination. More tests = steadier numbers, slower run.
              </InfoTip>
            </label>
            <select
              id="audit-percell"
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
            {busy ? (
              <>
                <Loader2 className="animate-spin" />
                Running…
              </>
            ) : (
              <>
                <Play />
                Run audit
              </>
            )}
          </Button>
        </CardContent>
      </Card>

      <p className="-mt-2 text-xs leading-relaxed text-muted-foreground">
        We deliver the <span className="text-foreground">exact same good answer</span>{" "}
        in many accents and names, so everyone earns a pass. Any pass/fail gap is
        therefore the AI being unfair — not the person. Runs on made-up data, no
        keys needed.
      </p>

      {error && (
        <div
          className="rounded-lg border border-destructive/40 bg-destructive/10 p-4 text-sm text-destructive"
          role="alert"
        >
          {error}
        </div>
      )}

      {audit ? (
        <AuditView audit={audit} />
      ) : (
        <div className="rounded-lg border border-dashed border-border p-10 text-center text-sm text-muted-foreground">
          No audit yet — pick a scenario and run one.
        </div>
      )}
    </div>
  );
}
