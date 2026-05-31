// Typed client for the FairBench control-plane. Every call is same-origin
// (/api/*) and proxied to FastAPI by the Next rewrites in next.config.js.

export type GroupStat = {
  pass_rate: number;
  impact_ratio: number | null;
  adverse_impact: boolean;
  n: number;
};

export type AsrBiasRow = {
  group: string;
  avg_wer: number;
  gap_vs_best: number;
};

export type Audit = {
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
  asr_bias: AsrBiasRow[];
  verdict: string;
  scenario?: string;
  source?: string;
  result_id?: string;
};

export type ScenarioInfo = {
  id: string;
  title: string;
  domain: string;
  pass_overall: number;
  persona_name: string;
  opening_line: string;
  criteria: string[];
};

export type Turn = { role: string; text: string };

export type SessionSummary = {
  session_id: string;
  scenario_id: string;
  created_at?: string | null;
  source?: string | null;
  behavior?: string | null;
  accent?: string | null;
  passed?: boolean | null;
  overall?: number | null;
  asr_wer?: number | null;
  turns: number;
};

export type SessionDetail = {
  session_id: string;
  scenario_id: string;
  created_at?: string;
  turns: Turn[];
  metadata?: Record<string, unknown>;
  grade?: SessionGrade;
};

export type SessionGrade = {
  scenario_id: string;
  session_id: string;
  competency_scores: Record<string, number>;
  overall: number;
  passed: boolean;
  evidence: { criterion: string; matched: string[] }[];
};

export type GradeResponse = { session_id: string; grade: SessionGrade };

export type LiveFeedback = {
  overall: number;
  passed: boolean;
  scores: Record<string, number>;
  met: string[];
  partial: string[];
  unmet: string[];
  target: string | null;
  hint: string;
  criteria_names: Record<string, string>;
};

export type CompareAttr = {
  worst_before: number | null;
  worst_after: number | null;
  gain: number | null;
  flagged_before: number;
  flagged_after: number;
};

export type CompareSummary = {
  headline_attr: string | null;
  headline_before: number | null;
  headline_after: number | null;
  headline_gain: number | null;
  by_attribute: Record<string, CompareAttr>;
  flagged_before: number;
  flagged_after: number;
  false_fail_before: number | null;
  false_fail_after: number | null;
  verdict_before: string;
  verdict_after: string;
};

export type AuditCompare = {
  before: Audit;
  after: Audit;
  summary: CompareSummary;
};

export type CompareBody = {
  scenario: string;
  per_cell?: number;
  seed?: number | null;
  before_bias_rate?: number;
  after_bias_rate?: number;
};

export type TwilioCall = {
  sid: string;
  status: string;
  to?: string;
  scenario?: string;
  mode?: "agent" | "say";
  duration?: string | null;
};

export type TwilioInfo = {
  enabled: boolean;
  configured: boolean;
  phone_number: string;
  voice_webhook: string;
};

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

async function http<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(path, {
      ...init,
      headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
      cache: "no-store",
    });
  } catch (e) {
    throw new ApiError(
      `Cannot reach the control-plane. Is fairbench-server running on :8000? (${
        (e as Error).message
      })`,
      0,
    );
  }
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const body = await res.json();
      if (body?.detail) detail = String(body.detail);
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(detail, res.status);
  }
  return (await res.json()) as T;
}

export type AuditRunBody = {
  scenario: string;
  per_cell?: number;
  seed?: number | null;
  grader_name_bias_rate?: number;
};

export const api = {
  scenarios: () => http<ScenarioInfo[]>("/api/scenarios"),
  latestAudit: () => http<Audit>("/api/audit"),
  runAudit: (body: AuditRunBody) =>
    http<Audit>("/api/audit/run", { method: "POST", body: JSON.stringify(body) }),
  sessions: () => http<SessionSummary[]>("/api/sessions"),
  session: (id: string) => http<SessionDetail>(`/api/sessions/${encodeURIComponent(id)}`),
  grade: (body: { scenario_id: string; turns: Turn[]; session_id?: string }) =>
    http<GradeResponse>("/api/sessions/grade", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  feedback: (body: { scenario_id: string; turns: Turn[] }) =>
    http<LiveFeedback>("/api/feedback", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  compareAudit: (body: CompareBody) =>
    http<AuditCompare>("/api/audit/compare", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  cekuraResult: (id: string) =>
    http<Audit>(`/api/cekura/result/${encodeURIComponent(id)}`),
  cekuraBatteryEstimate: (scenario: string) =>
    http<{ scenario: string; per_cell: number; expected_calls: number }>(
      `/api/cekura/battery/estimate?scenario=${encodeURIComponent(scenario)}`,
    ),
  cekuraBattery: (scenario: string) =>
    http<Audit>(`/api/cekura/battery?scenario=${encodeURIComponent(scenario)}`),
  twilioInfo: () => http<TwilioInfo>("/api/twilio/info"),
  placeCall: (to: string, scenario: string) =>
    http<TwilioCall>("/api/twilio/call", {
      method: "POST",
      body: JSON.stringify({ to, scenario }),
    }),
  callStatus: (sid: string) =>
    http<TwilioCall>(`/api/twilio/call/${encodeURIComponent(sid)}`),
  setPhoneScenario: (scenario: string) =>
    http<{ active_scenario: string }>("/api/twilio/scenario", {
      method: "POST",
      body: JSON.stringify({ scenario }),
    }),
};
