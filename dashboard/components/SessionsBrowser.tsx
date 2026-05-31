"use client";

import { useEffect, useState } from "react";
import { Check, Loader2, RefreshCw } from "lucide-react";

import {
  api,
  ApiError,
  type ScenarioInfo,
  type SessionDetail,
  type SessionGrade,
  type SessionSummary,
  type Turn,
} from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

function relativeTime(iso?: string | null): string {
  if (!iso) return "";
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "";
  const mins = Math.round((Date.now() - then) / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.round(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.round(hrs / 24);
  if (days < 7) return `${days}d ago`;
  return new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

export function SessionsBrowser({
  scenarios = [],
}: {
  scenarios?: ScenarioInfo[];
}) {
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [detail, setDetail] = useState<SessionDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);

  // Map scenario ids → human titles / persona names so the list reads in plain
  // language instead of raw machine ids.
  const byId = new Map(scenarios.map((s) => [s.id, s]));
  const titleOf = (id: string) =>
    byId.get(id)?.title ?? id.replace(/_/g, " ");
  const personaOf = (id?: string) =>
    (id && byId.get(id)?.persona_name) || "Patient";

  async function load() {
    setLoading(true);
    setError(null);
    try {
      setSessions(await api.sessions());
    } catch (e) {
      setError(e instanceof ApiError ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function open(id: string) {
    setSelected(id);
    setDetail(null);
    setDetailError(null);
    try {
      setDetail(await api.session(id));
    } catch (e) {
      setDetailError(e instanceof ApiError ? e.message : String(e));
    }
  }

  return (
    <div className="grid gap-6 lg:grid-cols-[1.1fr_1.4fr]">
      <Card className="flex max-h-[36rem] flex-col">
        <CardHeader className="flex-row items-center justify-between space-y-0 pb-3">
          <CardTitle className="text-base">
            Past conversations
            <span className="ml-2 text-xs font-normal text-muted-foreground">
              {sessions.length === 0 ? "none yet" : `${sessions.length} total`}
            </span>
          </CardTitle>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => void load()}
            aria-label="Refresh conversations"
            title="Refresh"
          >
            <RefreshCw className={cn(loading && "animate-spin")} />
          </Button>
        </CardHeader>
        <CardContent className="scroll-thin flex-1 overflow-y-auto p-0">
          {loading ? (
            <div className="flex h-32 items-center justify-center text-muted-foreground">
              <Loader2 className="size-5 animate-spin" />
            </div>
          ) : error ? (
            <div className="p-5 text-sm text-destructive" role="alert">
              {error}
            </div>
          ) : sessions.length === 0 ? (
            <div className="p-5 text-sm text-muted-foreground">
              No conversations yet. Run an audit or a live call to generate some.
            </div>
          ) : (
            <ul className="divide-y divide-border">
              {sessions.map((s) => (
                <li key={s.session_id}>
                  <button
                    onClick={() => void open(s.session_id)}
                    className={cn(
                      "flex w-full items-center gap-3 px-5 py-3 text-left text-sm transition-colors hover:bg-accent/50",
                      selected === s.session_id && "bg-accent/60",
                    )}
                  >
                    <div className="min-w-0 flex-1">
                      <div className="truncate font-medium">
                        {titleOf(s.scenario_id)}
                      </div>
                      <div className="truncate text-xs text-muted-foreground">
                        {[
                          s.source,
                          s.accent ? `${s.accent} accent` : null,
                          relativeTime(s.created_at),
                        ]
                          .filter(Boolean)
                          .join(" · ") || s.session_id}
                      </div>
                    </div>
                    {s.overall != null && (
                      <span className="shrink-0 text-xs tabular-nums text-muted-foreground">
                        {(s.overall * 100).toFixed(0)}%
                      </span>
                    )}
                    {s.passed != null && (
                      <Badge variant={s.passed ? "success" : "destructive"}>
                        {s.passed ? "Pass" : "Fail"}
                      </Badge>
                    )}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      <Card className="flex max-h-[36rem] flex-col">
        <CardHeader className="pb-3">
          <CardTitle className="text-base">
            {detail ? titleOf(detail.scenario_id) : "Conversation detail"}
          </CardTitle>
          {detail?.created_at && (
            <p className="text-xs text-muted-foreground">
              {new Date(detail.created_at).toLocaleString()}
            </p>
          )}
        </CardHeader>
        <CardContent className="scroll-thin flex-1 overflow-y-auto">
          {!selected ? (
            <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
              Select a conversation to see its score and transcript.
            </div>
          ) : detailError ? (
            <div className="flex h-full flex-col items-center justify-center gap-3 text-center">
              <p className="text-sm text-destructive">
                Couldn&apos;t load this conversation.
              </p>
              <Button
                variant="outline"
                size="sm"
                onClick={() => selected && void open(selected)}
              >
                <RefreshCw />
                Try again
              </Button>
            </div>
          ) : !detail ? (
            <div className="flex h-32 items-center justify-center text-muted-foreground">
              <Loader2 className="size-5 animate-spin" />
            </div>
          ) : (
            <div className="space-y-4">
              {detail.grade && <GradeSummary grade={detail.grade} />}

              <div className="flex flex-wrap gap-1.5">
                {Object.entries(detail.metadata ?? {})
                  .filter(([, v]) => v != null && typeof v !== "object")
                  .map(([k, v]) => (
                    <Badge key={k} variant="outline">
                      {k.replace(/_/g, " ")}: {String(v)}
                    </Badge>
                  ))}
              </div>

              <div>
                <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  Transcript
                </p>
                <div className="space-y-3">
                  {(detail.turns ?? []).map((t: Turn, i: number) => (
                    <TurnBubble
                      key={i}
                      turn={t}
                      persona={personaOf(detail.scenario_id)}
                    />
                  ))}
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function TurnBubble({ turn, persona }: { turn: Turn; persona: string }) {
  const isYou = turn.role === "trainee";
  const speaker = isYou ? "You" : turn.role === "patient" ? persona : turn.role;
  return (
    <div className={cn("flex", isYou ? "justify-end" : "justify-start")}>
      <div
        className={cn(
          "max-w-[85%] rounded-lg px-3 py-2 text-sm",
          isYou ? "bg-primary/15" : "bg-secondary text-secondary-foreground",
        )}
      >
        <div className="mb-0.5 text-xs font-medium text-muted-foreground">
          {speaker}
        </div>
        {turn.text}
      </div>
    </div>
  );
}

function GradeSummary({ grade }: { grade: SessionGrade }) {
  const entries = Object.entries(grade.competency_scores);
  return (
    <div className="rounded-lg border border-border bg-secondary/30 p-4">
      <div className="flex items-center justify-between">
        <span className="text-sm font-semibold">Scorecard</span>
        <Badge variant={grade.passed ? "success" : "destructive"}>
          {grade.passed ? "Pass" : "Fail"} · {(grade.overall * 100).toFixed(0)}%
        </Badge>
      </div>
      <div className="mt-3 space-y-2">
        {entries.map(([id, score]) => (
          <div key={id} className="flex items-center gap-3 text-sm">
            <span className="w-40 shrink-0 truncate text-muted-foreground" title={id.replace(/_/g, " ")}>
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
            <span className="w-9 text-right tabular-nums text-xs text-muted-foreground">
              {(score * 100).toFixed(0)}%
            </span>
          </div>
        ))}
      </div>
      {grade.evidence?.some((e) => e.matched.length > 0) && (
        <div className="mt-3 border-t border-border pt-3">
          <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            What earned credit
          </p>
          <ul className="mt-1.5 space-y-1">
            {grade.evidence
              .filter((e) => e.matched.length > 0)
              .map((e) => (
                <li key={e.criterion} className="flex items-start gap-1.5 text-xs">
                  <Check className="mt-0.5 size-3 shrink-0 text-success" />
                  <span className="text-muted-foreground">
                    <span className="text-foreground">
                      {e.criterion.replace(/_/g, " ")}
                    </span>{" "}
                    — &ldquo;{e.matched[0]}&rdquo;
                  </span>
                </li>
              ))}
          </ul>
        </div>
      )}
    </div>
  );
}
