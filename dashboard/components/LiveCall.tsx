"use client";

import { useEffect, useRef, useState } from "react";
import {
  PipecatClient,
  type BotOutputData,
  type Participant,
  type RTVIMessage,
  type TranscriptData,
} from "@pipecat-ai/client-js";
import { SmallWebRTCTransport } from "@pipecat-ai/small-webrtc-transport";
import {
  Check,
  Globe,
  Lightbulb,
  Loader2,
  Mic,
  MicOff,
  Phone,
  PhoneCall,
  PhoneOff,
  PhoneOutgoing,
  Smartphone,
} from "lucide-react";

import {
  api,
  ApiError,
  type LiveFeedback,
  type ScenarioInfo,
  type SessionGrade,
  type Turn,
  type TwilioCall,
  type TwilioInfo,
} from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

const STUN = [{ urls: "stun:stun.l.google.com:19302" }];

type Status = "idle" | "connecting" | "live" | "grading" | "done" | "error";
type Mode = "browser" | "phone";

const STATUS_LABEL: Record<Status, string> = {
  idle: "Ready",
  connecting: "Connecting…",
  live: "Live",
  grading: "Grading…",
  done: "Call ended",
  error: "Error",
};

const SELECT_CLASS =
  "h-9 rounded-md border border-border bg-background px-3 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-60";

export function LiveCall({ scenarios }: { scenarios: ScenarioInfo[] }) {
  const [scenario, setScenario] = useState(
    scenarios[0]?.id ?? "pharmacy_tech_metformin",
  );
  const [mode, setMode] = useState<Mode>("browser");
  const [status, setStatus] = useState<Status>("idle");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [grade, setGrade] = useState<SessionGrade | null>(null);
  const [feedback, setFeedback] = useState<LiveFeedback | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [twilio, setTwilio] = useState<TwilioInfo | null>(null);
  const [micReady, setMicReady] = useState(false);
  const [micBusy, setMicBusy] = useState(false);
  const [micMsg, setMicMsg] = useState<{ kind: "ok" | "warn" | "error"; text: string } | null>(
    null,
  );

  const clientRef = useRef<PipecatClient | null>(null);
  const turnsRef = useRef<Turn[]>([]);
  const fbBusyRef = useRef(false);
  const endedRef = useRef(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const transcriptEndRef = useRef<HTMLDivElement | null>(null);

  const activeScenario = scenarios.find((s) => s.id === scenario);
  const live = status === "connecting" || status === "live";

  useEffect(() => {
    transcriptEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [turns]);

  // Disconnect if the component unmounts mid-call.
  useEffect(() => {
    return () => {
      clientRef.current?.disconnect().catch(() => undefined);
    };
  }, []);

  // Warn up front when the browser can't capture a mic. The most common cause is
  // running inside an embedded/preview browser (e.g. the in-IDE Electron view),
  // which silently sends no audio — the call connects but the agent never hears you.
  useEffect(() => {
    if (typeof navigator === "undefined") return;
    if (!navigator.mediaDevices?.getUserMedia) {
      setMicMsg({
        kind: "error",
        text: "This browser can’t reach a microphone — this is usually the in-app preview. Open http://localhost:3000 in Chrome or Edge to use the live call.",
      });
    } else if (/Electron/i.test(navigator.userAgent)) {
      setMicMsg({
        kind: "warn",
        text: "Looks like the in-app preview browser. It usually can’t capture your mic — if “Enable microphone” doesn’t prompt, open http://localhost:3000 in Chrome or Edge.",
      });
    }
  }, []);

  // Explicitly request mic permission on a user gesture so the browser actually
  // PROMPTS, and translate each failure into a specific, actionable message.
  async function enableMic(): Promise<boolean> {
    if (typeof navigator === "undefined" || !navigator.mediaDevices?.getUserMedia) {
      setMicMsg({
        kind: "error",
        text: "This browser can’t access a microphone (in-app preview). Open http://localhost:3000 in Chrome or Edge.",
      });
      return false;
    }
    setMicBusy(true);
    try {
      const s = await navigator.mediaDevices.getUserMedia({ audio: true });
      s.getTracks().forEach((t) => t.stop());
      setMicReady(true);
      setMicMsg({ kind: "ok", text: "Microphone ready." });
      return true;
    } catch (e) {
      const name = (e as DOMException)?.name;
      if (name === "NotAllowedError" || name === "SecurityError") {
        setMicMsg({
          kind: "error",
          text: "Microphone blocked. Click the mic/camera icon in your browser’s address bar, choose Allow, then click Enable microphone again.",
        });
      } else if (name === "NotFoundError" || name === "DevicesNotFoundError") {
        setMicMsg({ kind: "error", text: "No microphone found. Connect one and try again." });
      } else {
        setMicMsg({
          kind: "error",
          text: "Couldn’t access the microphone. Open http://localhost:3000 in Chrome or Edge and allow mic access.",
        });
      }
      setMicReady(false);
      return false;
    } finally {
      setMicBusy(false);
    }
  }

  // Phone mode: fetch the configured number once, and tell the server which
  // scenario the next inbound call should run (the TwiML endpoint reads it).
  useEffect(() => {
    if (mode !== "phone") return;
    let cancelled = false;
    void api.twilioInfo().then(
      (info) => !cancelled && setTwilio(info),
      () => !cancelled && setTwilio(null),
    );
    void api.setPhoneScenario(scenario).catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [mode, scenario]);

  function push(role: Turn["role"], text: string) {
    const clean = text?.trim();
    if (!clean) return;
    turnsRef.current = [...turnsRef.current, { role, text: clean }];
    setTurns(turnsRef.current);
  }

  // Immediate per-turn coaching: re-grade the transcript-so-far after each
  // trainee utterance. The grader is keyword-based, so this is instant.
  async function refreshFeedback(scenarioId: string) {
    if (fbBusyRef.current) return;
    const captured = turnsRef.current;
    if (!captured.some((t) => t.role === "trainee" && t.text)) return;
    fbBusyRef.current = true;
    try {
      setFeedback(await api.feedback({ scenario_id: scenarioId, turns: captured }));
    } catch {
      /* live coaching is best-effort — never surface its errors mid-call */
    } finally {
      fbBusyRef.current = false;
    }
  }

  async function start() {
    setError(null);
    setGrade(null);
    setFeedback(null);
    setTurns([]);
    turnsRef.current = [];
    endedRef.current = false;

    // Ensure mic permission first (prompts if not yet granted). Abort cleanly with
    // a specific message rather than connecting into a silently dead call.
    if (!micReady) {
      const ok = await enableMic();
      if (!ok) {
        setStatus("idle");
        return;
      }
    }

    setStatus("connecting");

    const client = new PipecatClient({
      transport: new SmallWebRTCTransport({ iceServers: STUN }),
      enableMic: true,
      enableCam: false,
      callbacks: {
        onBotReady: () => setStatus("live"),
        onUserTranscript: (d: TranscriptData) => {
          if (d.final) {
            push("trainee", d.text);
            void refreshFeedback(scenario);
          }
        },
        onBotOutput: (d: BotOutputData) => {
          // onBotOutput fires per word and per sentence; keep the sentence
          // aggregation for a clean transcript (fall back if unlabeled).
          if (!d.aggregated_by || d.aggregated_by === "sentence") {
            push("patient", d.text);
          }
        },
        onTrackStarted: (track: MediaStreamTrack, participant?: Participant) => {
          if (
            participant &&
            !participant.local &&
            track.kind === "audio" &&
            audioRef.current
          ) {
            audioRef.current.srcObject = new MediaStream([track]);
          }
        },
        onBotDisconnected: () => {
          void endCall();
        },
        onError: (m: RTVIMessage) => {
          const data = m?.data as { message?: string } | undefined;
          setError(data?.message ?? "Voice pipeline error");
          setStatus("error");
        },
      },
    });
    clientRef.current = client;

    try {
      await client.connect({
        webrtcRequestParams: {
          endpoint: "/api/offer",
          requestData: { scenario },
        },
      });
      setStatus((s) => (s === "connecting" ? "live" : s));
    } catch (e) {
      setError(
        e instanceof ApiError
          ? e.message
          : (e as Error)?.message ?? "Failed to connect — is the voice stack running?",
      );
      setStatus("error");
    }
  }

  async function endCall() {
    if (endedRef.current) return;
    endedRef.current = true;

    await clientRef.current?.disconnect().catch(() => undefined);

    const captured = turnsRef.current;
    const hasTrainee = captured.some((t) => t.role === "trainee" && t.text);
    if (!hasTrainee) {
      setStatus("done");
      return;
    }

    setStatus("grading");
    try {
      const res = await api.grade({ scenario_id: scenario, turns: captured });
      setGrade(res.grade);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : String(e));
    } finally {
      setStatus("done");
    }
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_1.1fr]">
      {/* Controls + scenario brief */}
      <div className="space-y-6">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="flex items-center justify-between text-base">
              <span className="flex items-center gap-2">
                <PhoneCall className="size-4 text-muted-foreground" />
                Live voice call
              </span>
              {mode === "browser" && <StatusPill status={status} />}
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <ModeToggle mode={mode} setMode={setMode} disabled={live || status === "grading"} />

            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-medium text-muted-foreground">
                Scenario
              </label>
              <select
                className={SELECT_CLASS}
                value={scenario}
                onChange={(e) => setScenario(e.target.value)}
                disabled={live || status === "grading"}
              >
                {scenarios.length === 0 && (
                  <option value={scenario}>{scenario}</option>
                )}
                {scenarios.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.title}
                  </option>
                ))}
              </select>
            </div>

            {mode === "browser" ? (
              <>
                {!micReady && !live && (
                  <div className="flex flex-col gap-2 rounded-md border border-border bg-secondary/30 p-3">
                    <div className="flex items-center justify-between gap-3">
                      <span className="flex items-center gap-2 text-sm">
                        <MicOff className="size-4 text-muted-foreground" />
                        Microphone not enabled
                      </span>
                      <Button size="sm" variant="outline" onClick={() => void enableMic()} disabled={micBusy}>
                        {micBusy ? <Loader2 className="animate-spin" /> : <Mic />}
                        Enable microphone
                      </Button>
                    </div>
                    <p className="text-xs leading-relaxed text-muted-foreground">
                      We’ll ask your browser for mic access. If no prompt appears,
                      you’re likely in the in-app preview — open{" "}
                      <span className="text-foreground">http://localhost:3000</span>{" "}
                      in Chrome or Edge.
                    </p>
                  </div>
                )}

                {micMsg && (
                  <div
                    className={cn(
                      "rounded-md border p-3 text-xs leading-relaxed",
                      micMsg.kind === "ok"
                        ? "border-success/40 bg-success/10 text-foreground"
                        : micMsg.kind === "warn"
                          ? "border-warning/40 bg-warning/10 text-foreground"
                          : "border-destructive/40 bg-destructive/10 text-destructive",
                    )}
                  >
                    {micMsg.kind === "ok" && <Check className="mr-1 inline size-3.5" />}
                    {micMsg.text}
                  </div>
                )}

                <div className="flex gap-2">
                  {!live ? (
                    <Button onClick={start} disabled={status === "grading" || micBusy}>
                      <Mic />
                      {micReady ? "Start call" : "Enable mic & start"}
                    </Button>
                  ) : (
                    <Button variant="destructive" onClick={() => void endCall()}>
                      <PhoneOff />
                      Hang up & grade
                    </Button>
                  )}
                </div>

                <p className="text-xs leading-relaxed text-muted-foreground">
                  Speak into your mic as the trainee. Nemotron transcribes, the
                  Nemotron LLM voices the{" "}
                  {activeScenario?.persona_name ?? "patient"}, and Gradium speaks
                  the reply. On hang-up the captured transcript is graded against
                  the rubric — the same grader the audit battery uses.
                </p>

                {error && (
                  <div className="rounded-md border border-destructive/40 bg-destructive/10 p-3 text-xs text-destructive">
                    {error}
                  </div>
                )}
              </>
            ) : (
              <PhonePanel
                twilio={twilio}
                scenario={scenario}
                personaName={activeScenario?.persona_name}
              />
            )}
          </CardContent>
        </Card>

        {feedback && status !== "done" && status !== "idle" && (
          <CoachPanel fb={feedback} />
        )}

        {activeScenario && (
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm">{activeScenario.title}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <p className="text-muted-foreground">
                <span className="text-foreground">Opening line — </span>
                “{activeScenario.opening_line}”
              </p>
              {activeScenario.criteria.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {activeScenario.criteria.map((c) => (
                    <Badge key={c} variant="outline">
                      {c.replace(/_/g, " ")}
                    </Badge>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        )}
      </div>

      {/* Transcript + grade (browser) · where-results-land (phone) */}
      <div className="space-y-6">
        {mode === "phone" ? (
          <PhoneResultsCard />
        ) : (
          <>
            <Card className="flex h-[26rem] flex-col">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm text-muted-foreground">
                  Transcript
                </CardTitle>
              </CardHeader>
              <CardContent className="scroll-thin flex-1 overflow-y-auto">
                {turns.length === 0 ? (
                  <div className="flex h-full items-center justify-center text-center text-sm text-muted-foreground">
                    {live
                      ? "Listening… start speaking."
                      : "Start a call to see the live transcript."}
                  </div>
                ) : (
                  <div className="space-y-3">
                    {turns.map((t, i) => (
                      <TurnBubble key={i} turn={t} />
                    ))}
                    <div ref={transcriptEndRef} />
                  </div>
                )}
              </CardContent>
            </Card>

            {grade && <GradeCard grade={grade} />}
          </>
        )}
      </div>

      <audio ref={audioRef} autoPlay playsInline className="hidden" />
    </div>
  );
}

function StatusPill({ status }: { status: Status }) {
  const tone =
    status === "live"
      ? "success"
      : status === "error"
        ? "destructive"
        : status === "connecting" || status === "grading"
          ? "warning"
          : "outline";
  return (
    <Badge variant={tone as never} className="gap-1.5">
      {(status === "connecting" || status === "grading") && (
        <Loader2 className="size-3 animate-spin" />
      )}
      {status === "live" && (
        <span className="size-2 animate-pulse rounded-full bg-success" />
      )}
      {STATUS_LABEL[status]}
    </Badge>
  );
}

function TurnBubble({ turn }: { turn: Turn }) {
  const isTrainee = turn.role === "trainee";
  return (
    <div className={cn("flex", isTrainee ? "justify-end" : "justify-start")}>
      <div
        className={cn(
          "max-w-[85%] rounded-lg px-3 py-2 text-sm",
          isTrainee
            ? "bg-primary/15 text-foreground"
            : "bg-secondary text-secondary-foreground",
        )}
      >
        <div className="mb-0.5 text-[0.65rem] uppercase tracking-wider text-muted-foreground">
          {turn.role}
        </div>
        {turn.text}
      </div>
    </div>
  );
}

function CoachPanel({ fb }: { fb: LiveFeedback }) {
  const label = (id: string) => fb.criteria_names[id] ?? id.replace(/_/g, " ");
  const tone = fb.passed ? "success" : fb.overall >= 0.5 ? "warning" : "secondary";
  return (
    <Card className="animate-fade-in border-primary/30">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center justify-between text-base">
          <span className="flex items-center gap-2">
            <Lightbulb className="size-4 text-primary" />
            Live coaching
          </span>
          <Badge variant={tone as never}>{(fb.overall * 100).toFixed(0)}%</Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="rounded-md border border-primary/30 bg-primary/10 p-3 text-sm">
          <span className="font-semibold text-primary">Next →</span> {fb.hint}
        </div>
        <div className="flex flex-wrap gap-1.5">
          {fb.met.map((c) => (
            <Badge key={c} variant="success" className="gap-1">
              <Check className="size-3" />
              {label(c)}
            </Badge>
          ))}
          {fb.partial.map((c) => (
            <Badge key={c} variant="warning">
              {label(c)}
            </Badge>
          ))}
          {fb.unmet.map((c) => (
            <Badge key={c} variant="outline">
              {label(c)}
            </Badge>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function ModeToggle({
  mode,
  setMode,
  disabled,
}: {
  mode: Mode;
  setMode: (m: Mode) => void;
  disabled: boolean;
}) {
  const opts: { id: Mode; label: string; icon: typeof Globe }[] = [
    { id: "browser", label: "In browser", icon: Globe },
    { id: "phone", label: "On the phone", icon: Smartphone },
  ];
  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-xs font-medium text-muted-foreground">
        Practice mode
      </label>
      <div className="grid grid-cols-2 gap-1 rounded-lg border border-border bg-secondary/50 p-1">
        {opts.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            type="button"
            disabled={disabled}
            onClick={() => setMode(id)}
            className={cn(
              "flex items-center justify-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors disabled:opacity-50",
              mode === id
                ? "bg-card text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground",
            )}
          >
            <Icon className="size-4" />
            {label}
          </button>
        ))}
      </div>
    </div>
  );
}

function formatPhone(raw: string): string {
  const m = raw.match(/^\+1(\d{3})(\d{3})(\d{4})$/);
  return m ? `+1 (${m[1]}) ${m[2]}-${m[3]}` : raw;
}

const CALL_TERMINAL = new Set([
  "completed",
  "failed",
  "busy",
  "no-answer",
  "canceled",
]);

function PhonePanel({
  twilio,
  scenario,
  personaName,
}: {
  twilio: TwilioInfo | null;
  scenario: string;
  personaName?: string;
}) {
  const [to, setTo] = useState("");
  const [call, setCall] = useState<TwilioCall | null>(null);
  const [calling, setCalling] = useState(false);
  const [callErr, setCallErr] = useState<string | null>(null);

  const status = call?.status ?? "";
  const active = Boolean(call) && !CALL_TERMINAL.has(status);

  // Poll live call status until it reaches a terminal state.
  useEffect(() => {
    const sid = call?.sid;
    if (!sid || CALL_TERMINAL.has(status)) return;
    const t = setInterval(async () => {
      try {
        const s = await api.callStatus(sid);
        setCall((prev) => (prev && prev.sid === sid ? { ...prev, ...s } : prev));
      } catch {
        /* transient — keep the last known status and retry */
      }
    }, 1500);
    return () => clearInterval(t);
  }, [call?.sid, status]);

  async function callMe() {
    setCallErr(null);
    setCall(null);
    const num = to.trim().replace(/[\s-]/g, "");
    if (!/^\+[1-9]\d{6,14}$/.test(num)) {
      setCallErr("Enter your number in E.164 format, e.g. +14155551234.");
      return;
    }
    setCalling(true);
    try {
      setCall(await api.placeCall(num, scenario));
    } catch (e) {
      setCallErr(e instanceof ApiError ? e.message : String(e));
    } finally {
      setCalling(false);
    }
  }

  if (twilio === null) {
    return (
      <div className="flex items-center gap-2 rounded-md border border-border bg-secondary/30 p-3 text-sm text-muted-foreground">
        <Loader2 className="size-4 animate-spin" />
        Checking phone setup…
      </div>
    );
  }

  const ready = twilio.enabled && twilio.configured && Boolean(twilio.phone_number);

  if (!ready) {
    return (
      <div className="space-y-2 rounded-md border border-warning/40 bg-warning/10 p-3 text-sm">
        <p className="font-medium text-foreground">Phone practice isn’t set up yet.</p>
        <p className="text-muted-foreground">
          Add <code className="text-foreground">TWILIO_ACCOUNT_SID</code>,{" "}
          <code className="text-foreground">TWILIO_AUTH_TOKEN</code>, and{" "}
          <code className="text-foreground">TWILIO_PHONE_NUMBER</code> to{" "}
          <code className="text-foreground">.env</code>, then restart the server.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Have it call you — the primary, works-right-now path */}
      <div className="space-y-3 rounded-lg border border-primary/40 bg-primary/5 p-4">
        <div className="flex items-center gap-2">
          <PhoneOutgoing className="size-4 text-primary" />
          <span className="text-sm font-semibold text-foreground">Have it call you</span>
        </div>
        <div className="flex flex-col gap-2 sm:flex-row">
          <input
            type="tel"
            inputMode="tel"
            className="h-10 flex-1 rounded-md border border-border bg-background px-3 text-sm tabular-nums focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            placeholder="+1 415 555 1234"
            value={to}
            onChange={(e) => setTo(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !calling && !active && callMe()}
            disabled={calling || active}
          />
          <Button onClick={callMe} disabled={calling || active || !to.trim()}>
            {calling || active ? (
              <Loader2 className="animate-spin" />
            ) : (
              <PhoneCall />
            )}
            {active ? "On the line…" : "Call me"}
          </Button>
        </div>

        {callErr && (
          <div className="rounded-md border border-destructive/40 bg-destructive/10 p-2.5 text-xs text-destructive">
            {callErr}
          </div>
        )}

        {call && <CallProgress call={call} />}

        <p className="text-[0.72rem] leading-relaxed text-muted-foreground">
          We dial your phone from{" "}
          <span className="tabular-nums text-foreground">
            {formatPhone(twilio.phone_number)}
          </span>{" "}
          and the agent answers as{" "}
          <span className="text-foreground">{personaName ?? "the patient"}</span>.
          {call?.mode === "say" && (
            <>
              {" "}
              Without a public server URL the call rings and speaks the opening line;
              set <code className="text-foreground">PUBLIC_BASE_URL</code> (e.g. an
              ngrok https URL) for the full interactive agent.
            </>
          )}{" "}
          On a trial account the number must be{" "}
          <span className="text-foreground">verified in Twilio</span> first.
        </p>
      </div>

      {/* Or dial in yourself */}
      <a
        href={`tel:${twilio.phone_number}`}
        className="flex items-center gap-3 rounded-lg border border-border bg-card p-4 transition-colors hover:bg-secondary"
      >
        <span className="flex size-10 items-center justify-center rounded-full bg-primary/10">
          <Phone className="size-5 text-primary" />
        </span>
        <span>
          <span className="block text-[0.7rem] font-medium uppercase tracking-wider text-muted-foreground">
            Or dial in yourself
          </span>
          <span className="block text-lg font-bold tabular-nums text-foreground">
            {formatPhone(twilio.phone_number)}
          </span>
        </span>
      </a>
    </div>
  );
}

const CALL_STEPS = [
  { label: "Queued", match: ["queued", "initiated"] },
  { label: "Ringing", match: ["ringing"] },
  { label: "In progress", match: ["in-progress"] },
  { label: "Completed", match: ["completed"] },
];

function callStep(status: string): number {
  const i = CALL_STEPS.findIndex((s) => s.match.includes(status));
  return i;
}

function CallProgress({ call }: { call: TwilioCall }) {
  const status = call.status;
  const bad = ["failed", "busy", "no-answer", "canceled"].includes(status);
  const idx = bad ? CALL_STEPS.length : callStep(status);

  return (
    <div className="space-y-2.5 rounded-md border border-border bg-background p-3">
      <div className="flex items-center justify-between">
        <span className="font-mono text-[0.7rem] text-muted-foreground">
          {call.sid}
        </span>
        <Badge variant={bad ? "destructive" : status === "completed" ? "success" : "default"}>
          {bad ? status.replace(/-/g, " ") : status === "completed" ? "completed" : "live"}
        </Badge>
      </div>

      {bad ? (
        <div className="flex items-center gap-2 text-sm text-destructive">
          <PhoneOff className="size-4" />
          Call {status.replace(/-/g, " ")}
          {status === "no-answer" && " — try answering when it rings."}
        </div>
      ) : (
        <div className="flex items-center gap-1">
          {CALL_STEPS.map((s, i) => {
            const done = i < idx || status === "completed";
            const here = i === idx && status !== "completed";
            return (
              <div key={s.label} className="flex flex-1 flex-col items-center gap-1.5">
                <div className="flex w-full items-center">
                  <span
                    className={cn(
                      "flex size-6 shrink-0 items-center justify-center rounded-full border text-[0.65rem]",
                      done
                        ? "border-success bg-success/15 text-success"
                        : here
                          ? "border-primary bg-primary/15 text-primary"
                          : "border-border text-muted-foreground",
                    )}
                  >
                    {done ? (
                      <Check className="size-3" />
                    ) : here ? (
                      <Loader2 className="size-3 animate-spin" />
                    ) : (
                      i + 1
                    )}
                  </span>
                  {i < CALL_STEPS.length - 1 && (
                    <span
                      className={cn(
                        "h-0.5 flex-1",
                        i < idx ? "bg-success" : "bg-border",
                      )}
                    />
                  )}
                </div>
                <span
                  className={cn(
                    "text-[0.62rem] leading-tight",
                    done || here ? "text-foreground" : "text-muted-foreground/60",
                  )}
                >
                  {s.label}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function PhoneResultsCard() {
  return (
    <Card className="flex h-[26rem] flex-col items-center justify-center text-center">
      <CardContent className="max-w-xs space-y-3 p-6">
        <span className="mx-auto flex size-12 items-center justify-center rounded-full bg-primary/10">
          <Smartphone className="size-6 text-primary" />
        </span>
        <p className="text-sm font-medium text-foreground">
          Practice on a real phone call
        </p>
        <p className="text-sm leading-relaxed text-muted-foreground">
          On a phone call the transcript is captured server-side, so it won’t
          stream here. When you hang up, the graded session appears in the{" "}
          <span className="text-foreground">Sessions</span> tab — same rubric,
          same audit.
        </p>
      </CardContent>
    </Card>
  );
}

function GradeCard({ grade }: { grade: SessionGrade }) {
  const entries = Object.entries(grade.competency_scores);
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center justify-between text-base">
          Grade
          <Badge variant={grade.passed ? "success" : "destructive"}>
            {grade.passed ? "PASS" : "FAIL"} · {(grade.overall * 100).toFixed(0)}%
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2.5">
        {entries.map(([id, score]) => (
          <div key={id} className="flex items-center gap-3 text-sm">
            <span className="w-44 shrink-0 truncate text-muted-foreground">
              {id.replace(/_/g, " ")}
            </span>
            <div className="h-2 flex-1 overflow-hidden rounded-full bg-secondary">
              <div
                className={cn(
                  "h-full rounded-full",
                  score >= 0.66
                    ? "bg-success"
                    : score >= 0.34
                      ? "bg-warning"
                      : "bg-destructive",
                )}
                style={{ width: `${Math.max(3, score * 100)}%` }}
              />
            </div>
            <span className="w-10 text-right tabular-nums text-xs text-muted-foreground">
              {(score * 100).toFixed(0)}%
            </span>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
