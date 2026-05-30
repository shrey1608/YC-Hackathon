import fs from "fs";
import path from "path";

export const dynamic = "force-dynamic";

type GroupStat = {
  pass_rate: number;
  impact_ratio: number | null;
  adverse_impact: boolean;
  n: number;
};
type Audit = {
  n_performances: number;
  fairness_cohort?: string;
  fairness_cohort_n?: number;
  reliability: {
    n: number;
    agreement: number | null;
    false_pass_rate?: number;
    false_fail_rate?: number;
  };
  fairness: Record<string, Record<string, GroupStat>>;
  asr_bias: { group: string; avg_wer: number; gap_vs_best: number }[];
  verdict: string;
};
type Session = {
  session_id: string;
  metadata?: {
    group?: { accent?: string };
    behavior?: string;
    passed?: boolean;
    asr_wer?: number;
    overall?: number;
  };
};

const ROOT = path.join(process.cwd(), "..");

function readAudit(): Audit | null {
  try {
    return JSON.parse(fs.readFileSync(path.join(ROOT, "reports", "audit.json"), "utf-8"));
  } catch {
    return null;
  }
}

function readSessions(): Session[] {
  try {
    const dir = path.join(ROOT, ".sessions");
    return fs
      .readdirSync(dir)
      .filter((f) => f.startsWith("syn-sim-") && f.endsWith(".json"))
      .map((f) => JSON.parse(fs.readFileSync(path.join(dir, f), "utf-8")))
      .sort((a, b) =>
        (a.metadata?.group?.accent || "").localeCompare(b.metadata?.group?.accent || ""),
      );
  } catch {
    return [];
  }
}

function irColor(s: GroupStat): string {
  if (s.adverse_impact) return "var(--red)";
  const ir = s.impact_ratio ?? 1;
  if (ir < 0.9) return "var(--amber)";
  return "var(--green)";
}

function pct(x: number | null | undefined): string {
  return x == null ? "—" : `${(x * 100).toFixed(1)}%`;
}

function Bar({ value, color }: { value: number; color: string }) {
  return (
    <span className="bar">
      <span style={{ width: `${Math.max(2, Math.min(100, value * 100))}%`, background: color }} />
    </span>
  );
}

export default function Home() {
  const audit = readAudit();
  const sessions = readSessions();

  if (!audit) {
    return (
      <main className="wrap">
        <h1>FairBench</h1>
        <p className="muted">
          No audit found. Run <code>fairbench demo</code> from the project root to generate{" "}
          <code>reports/audit.json</code>.
        </p>
      </main>
    );
  }

  const review = audit.verdict.startsWith("REVIEW");
  const rel = audit.reliability;
  const maxWer = Math.max(0.01, ...audit.asr_bias.map((a) => a.avg_wer));

  return (
    <main className="wrap">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h1 style={{ margin: 0 }}>FairBench</h1>
        <span className="badge">synthetic data only</span>
      </div>
      <p className="muted" style={{ marginTop: ".35rem" }}>
        Voice competency training with integrity auditing — impact ratios, grader reliability, and
        ASR-bias, so every pass/fail is defensible.
      </p>

      <div className={`banner ${review ? "review" : "pass"}`}>{audit.verdict}</div>

      <div className="cards">
        <div className="card">
          <div className="k">Performances</div>
          <div className="v">{audit.n_performances}</div>
        </div>
        <div className="card">
          <div className="k">Qualified cohort</div>
          <div className="v">{audit.fairness_cohort_n ?? "—"}</div>
        </div>
        <div className="card">
          <div className="k">Grader agreement</div>
          <div className="v">{pct(rel.agreement)}</div>
        </div>
        <div className="card">
          <div className="k">False-fail rate</div>
          <div className="v">{pct(rel.false_fail_rate)}</div>
        </div>
      </div>

      {Object.entries(audit.fairness).map(([attr, groups]) => (
        <section key={attr}>
          <h2>
            Fairness — {attr.replace("_", " ")}{" "}
            <span className="muted" style={{ fontWeight: 400, fontSize: ".8rem" }}>
              (4/5ths rule)
            </span>
          </h2>
          <table>
            <thead>
              <tr>
                <th>Group</th>
                <th>Pass rate</th>
                <th>Impact ratio</th>
                <th>N</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(groups)
                .sort((a, b) => (a[1].impact_ratio ?? 1) - (b[1].impact_ratio ?? 1))
                .map(([g, s]) => (
                  <tr key={g}>
                    <td>{g}</td>
                    <td>{pct(s.pass_rate)}</td>
                    <td>
                      <Bar value={s.impact_ratio ?? 1} color={irColor(s)} />
                      {s.impact_ratio == null ? "—" : s.impact_ratio.toFixed(3)}
                    </td>
                    <td>{s.n}</td>
                    <td>
                      {s.adverse_impact ? (
                        <span className="flag">ADVERSE IMPACT</span>
                      ) : (
                        <span className="ok">ok</span>
                      )}
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </section>
      ))}

      <section>
        <h2>ASR bias (transcription word-error rate by accent)</h2>
        {audit.asr_bias.length === 0 ? (
          <p className="muted">No ASR-bias gap detected — accent disparity, if any, is the grader.</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Accent</th>
                <th>Avg WER</th>
                <th>Gap vs best</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {audit.asr_bias.map((a) => (
                <tr key={a.group}>
                  <td>{a.group}</td>
                  <td>{a.avg_wer.toFixed(3)}</td>
                  <td>+{a.gap_vs_best.toFixed(3)}</td>
                  <td>
                    <Bar value={a.avg_wer / maxWer} color="var(--amber)" />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      {sessions.length > 0 && (
        <section>
          <h2>
            Same competent performance, graded across accents{" "}
            <span className="muted" style={{ fontWeight: 400, fontSize: ".8rem" }}>
              (identical good_tech script)
            </span>
          </h2>
          <table>
            <thead>
              <tr>
                <th>Accent</th>
                <th>Behavior</th>
                <th>Overall</th>
                <th>Realized WER</th>
                <th>Result</th>
              </tr>
            </thead>
            <tbody>
              {sessions.map((s) => (
                <tr key={s.session_id}>
                  <td>{s.metadata?.group?.accent ?? "—"}</td>
                  <td>{s.metadata?.behavior ?? "—"}</td>
                  <td>{s.metadata?.overall ?? "—"}</td>
                  <td>{s.metadata?.asr_wer ?? "—"}</td>
                  <td>
                    {s.metadata?.passed ? (
                      <span className="ok">pass</span>
                    ) : (
                      <span className="flag">FAIL</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      <div className="foot">
        Built on Pipecat, NVIDIA Nemotron (AWS), Gradium, Twilio, and Cekura. Fairness measured on
        the qualified cohort ({audit.fairness_cohort_n ?? audit.n_performances} performances).
        Synthetic personas and public rubrics only.
      </div>
    </main>
  );
}
