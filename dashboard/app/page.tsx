import { Fragment } from "react";
import Link from "next/link";
import {
  Activity,
  ArrowRight,
  Briefcase,
  Cpu,
  FlaskConical,
  Mic,
  Pill,
  RefreshCw,
  Scale,
  ShieldCheck,
  Sparkles,
  Stethoscope,
  Waves,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";

export const metadata = {
  title: "FairBench — Is your voice agent's evaluation fair?",
  description:
    "FairBench tests whether AI that scores people is fair: it gives the same competent answer in many accents and names and checks whether the AI passes everyone equally.",
};

export default function Landing() {
  return (
    <main className="min-h-screen">
      {/* Nav */}
      <nav className="container flex max-w-[1100px] items-center justify-between py-5">
        <div className="flex items-center gap-3">
          <div className="flex size-9 items-center justify-center rounded-lg bg-primary/15 text-lg font-bold text-primary">
            F
          </div>
          <span className="text-lg font-bold tracking-tight">FairBench</span>
        </div>
        <div className="flex items-center gap-3">
          <Link
            href="/app"
            className="inline-flex items-center gap-1.5 rounded-md bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground shadow-sm transition-colors hover:bg-primary/90"
          >
            Launch console
            <ArrowRight className="size-4" />
          </Link>
        </div>
      </nav>

      {/* Hero */}
      <section className="relative overflow-hidden border-b border-border">
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 -z-10 bg-gradient-to-b from-primary/10 via-background to-background"
        />
        <div className="container max-w-[1100px] py-20 sm:py-28">
          <Badge variant="secondary" className="mb-5 gap-1.5">
            <ShieldCheck className="size-3.5" />
            Bias testing for AI that scores people
          </Badge>
          <h1 className="max-w-3xl text-4xl font-bold leading-[1.1] tracking-tight sm:text-6xl">
            Is your voice agent grading{" "}
            <span className="text-primary">everyone</span> fairly?
          </h1>
          <p className="mt-6 max-w-2xl text-lg leading-relaxed text-muted-foreground">
            Voice AI now <span className="text-foreground">evaluates people</span> —
            screening job candidates, checking clinical skills, scoring language
            tests. FairBench gives the AI the{" "}
            <span className="text-foreground">exact same good answer</span> spoken
            in different accents, names, and genders, then checks: does it pass
            everyone equally? If not, it tells you{" "}
            <span className="text-foreground">why</span>.
          </p>
          <div className="mt-9 flex flex-wrap items-center gap-3">
            <Link
              href="/app"
              className="inline-flex items-center gap-2 rounded-lg bg-primary px-6 py-3 text-base font-semibold text-primary-foreground shadow-sm transition-colors hover:bg-primary/90"
            >
              See a live audit
              <ArrowRight className="size-5" />
            </Link>
            <a
              href="#how"
              className="inline-flex items-center gap-2 rounded-lg border border-border bg-card px-6 py-3 text-base font-medium text-foreground transition-colors hover:bg-secondary"
            >
              How it works
            </a>
          </div>
        </div>
      </section>

      {/* Concrete worked example — show, don't just tell */}
      <section className="border-b border-border bg-card">
        <div className="container max-w-[1100px] py-14">
          <p className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">
            What unfairness looks like
          </p>
          <h2 className="mt-2 max-w-2xl text-2xl font-bold tracking-tight">
            Same word-perfect answer. Two voices. Two different grades.
          </h2>
          <div className="mt-8 grid gap-4 md:grid-cols-3">
            <ExampleVoice
              kicker="Spoken in a US accent"
              line="“I'll verify your prescription and loop in the pharmacist.”"
              verdict="pass"
              score="PASS · 88%"
            />
            <ExampleVoice
              kicker="Identical words, Spanish accent"
              line="“I'll verify your prescription and loop in the pharmacist.”"
              verdict="fail"
              score="FAIL · 28%"
            />
            <div className="rounded-xl border border-primary/30 bg-primary/5 p-5">
              <p className="text-xs font-medium uppercase tracking-wider text-primary">
                FairBench verdict
              </p>
              <p className="mt-3 text-3xl font-bold tabular-nums text-foreground">
                0.31
              </p>
              <p className="text-xs text-muted-foreground">
                pass-rate vs. the top group (below the 0.80 fairness line)
              </p>
              <div className="mt-3 flex items-start gap-2.5">
                <Mic className="mt-0.5 size-4 shrink-0 text-primary" aria-hidden />
                <p className="text-sm leading-relaxed text-foreground">
                  <span className="font-semibold text-primary">Transcription bias.</span>{" "}
                  The speech-to-text mishears the accent, so the same good answer
                  fails — not because the speaker did worse. Fix the transcriber,
                  not the candidate.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* The two biases */}
      <section className="container max-w-[1100px] py-16 sm:py-20">
        <p className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">
          The problem
        </p>
        <h2 className="mt-2 max-w-2xl text-2xl font-bold tracking-tight">
          A spoken test can be unfair two ways — and neither shows up if you only
          test one speaker.
        </h2>
        <div className="mt-8 grid gap-5 md:grid-cols-2">
          <ProblemCard
            icon={<Waves className="size-5" />}
            tint="warning"
            title="Transcription bias"
            kicker="The speech-to-text mishears"
          >
            Accented speech gets transcribed with more errors, so an identical,
            correct answer is garbled before it&apos;s ever scored — and fails.
            The gap rides on the <i>speech-to-text</i>, not the speaker.
          </ProblemCard>
          <ProblemCard
            icon={<Scale className="size-5" />}
            tint="destructive"
            title="Grader bias"
            kicker="The AI judge under-credits"
          >
            The AI judge scores the same transcript lower based on a perceived
            identity (like the name it hears). Same words, lower score — a bias in
            the <i>judge</i>, with no transcription gap to explain it.
          </ProblemCard>
        </div>

        {/* Fairness clarifier */}
        <div className="mt-8 rounded-xl border border-primary/30 bg-primary/5 p-6">
          <div className="flex items-start gap-3">
            <ShieldCheck className="mt-0.5 size-5 shrink-0 text-primary" />
            <div>
              <p className="font-semibold text-foreground">
                What &ldquo;fair&rdquo; means here
              </p>
              <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">
                We&apos;re testing the <span className="text-foreground">AI&apos;s</span>{" "}
                fairness — not judging how anyone speaks. Because the{" "}
                <span className="text-foreground">exact same good answer</span> is
                delivered for every group, any gap in who passes is a flaw in the
                transcription or the judge. We measure it with the{" "}
                <span className="text-foreground">EEOC 80% rule</span> (a group
                passing less than 80% as often as the top group is a red flag) and
                then point to the cause, so you know exactly what to fix.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* How it works */}
      <section id="how" className="border-t border-border bg-secondary/30">
        <div className="container max-w-[1100px] py-16 sm:py-20">
          <p className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">
            How it works
          </p>
          <h2 className="mt-2 max-w-2xl text-2xl font-bold tracking-tight">
            Run a test, see the gaps, prove they closed.
          </h2>
          <div className="mt-8 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
            <StepCard
              n={1}
              icon={<Mic className="size-5" />}
              title="Practice"
              where="In browser or by phone"
            >
              Run a live spoken conversation against an AI counterpart. It&apos;s
              scored on a skills checklist, with{" "}
              <span className="text-foreground">live coaching</span> as you talk.
            </StepCard>
            <StepCard
              n={2}
              icon={<Activity className="size-5" />}
              title="Audit"
              where="Replay across identities"
            >
              Replay the same good answer across many accents, names &amp;
              genders. See who passes, the size of each gap, and{" "}
              <span className="text-foreground">what&apos;s causing it</span>.
            </StepCard>
            <StepCard
              n={3}
              icon={<Sparkles className="size-5" />}
              title="Improve"
              where="Fix &amp; re-test"
            >
              Apply a fix and re-run before/after in one click —{" "}
              <span className="text-foreground">prove the gap closed</span>, while
              the control group stays clean.
            </StepCard>
            <StepCard
              n={4}
              icon={<FlaskConical className="size-5" />}
              title="Validate"
              where="On real phone calls"
            >
              Run the identical test against a real, deployed agent over real
              calls, and get the <span className="text-foreground">same
              report</span> on live results.
            </StepCard>
          </div>
        </div>
      </section>

      {/* Self-improvement loop — now placed after the concepts are introduced */}
      <section className="border-t border-border">
        <div className="container max-w-[1100px] py-14 sm:py-16">
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div>
              <p className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">
                And it never stops
              </p>
              <h2 className="mt-2 max-w-2xl text-2xl font-bold tracking-tight">
                Every run feeds the next — gaps caught, explained, fixed, and
                re-checked, on a loop.
              </h2>
            </div>
            <span className="inline-flex items-center gap-2 rounded-full border border-primary/30 bg-primary/5 px-3 py-1.5 text-xs font-medium text-primary">
              <RefreshCw className="size-3.5 animate-spin [animation-duration:6s] motion-reduce:animate-none" />
              always on
            </span>
          </div>
          <LoopDiagram />
        </div>
      </section>

      {/* Use cases */}
      <section className="border-t border-border bg-secondary/30">
        <div className="container max-w-[1100px] py-16 sm:py-20">
          <p className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">
            Where it&apos;s used
          </p>
          <h2 className="mt-2 max-w-2xl text-2xl font-bold tracking-tight">
            Anywhere a voice AI decides who passes.
          </h2>
          <div className="mt-8 grid gap-5 lg:grid-cols-3">
            {USE_CASES.map((u) => (
              <UseCaseCard key={u.title} {...u} />
            ))}
          </div>
        </div>
      </section>

      {/* Bottom CTA */}
      <section className="container max-w-[1100px] py-16 text-center sm:py-24">
        <h2 className="text-3xl font-bold tracking-tight sm:text-4xl">
          See the bias — then watch it close.
        </h2>
        <p className="mx-auto mt-4 max-w-xl text-muted-foreground">
          The console runs entirely on made-up, public test personas — no real
          people and no keys needed to explore the report.
        </p>
        <Link
          href="/app"
          className="mt-8 inline-flex items-center gap-2 rounded-lg bg-primary px-7 py-3.5 text-base font-semibold text-primary-foreground shadow-sm transition-colors hover:bg-primary/90"
        >
          Launch console
          <ArrowRight className="size-5" />
        </Link>
      </section>

      <footer className="border-t border-border">
        <div className="container max-w-[1100px] py-6 text-xs leading-relaxed text-muted-foreground">
          Built on Pipecat, NVIDIA Nemotron, Gradium, Twilio, and Cekura.
          FairBench tests the evaluator, not the person: the same good answer is
          delivered for every group, so any pass/fail gap is bias in the
          transcription or the judge — not the speaker. Test personas are made-up
          and public.
        </div>
      </footer>
    </main>
  );
}

const LOOP: { icon: typeof Activity; title: string; sub: string }[] = [
  { icon: FlaskConical, title: "Run the test", sub: "real or simulated calls" },
  { icon: Activity, title: "Find the gaps", sub: "who passes, who doesn't" },
  { icon: Scale, title: "Explain why", sub: "mishearing vs. the judge" },
  { icon: Cpu, title: "Apply a fix", sub: "tune the judge / model" },
  { icon: ShieldCheck, title: "Fairer agent", sub: "gaps closed" },
];

function LoopDiagram() {
  return (
    <div className="mt-8 space-y-4">
      <div className="flex min-w-0 items-start gap-1 overflow-x-auto pb-2 scroll-thin sm:gap-2">
        {LOOP.map((step, i) => (
          <Fragment key={step.title}>
            <LoopNode step={step} i={i} />
            {i < LOOP.length - 1 && <LoopConnector />}
          </Fragment>
        ))}
        {/* loop-back: the last stage feeds the first */}
        <div className="flex shrink-0 flex-col items-center gap-2 self-center pl-1">
          <RefreshCw className="size-5 animate-spin text-primary [animation-duration:6s] motion-reduce:animate-none" />
          <span className="w-[88px] text-center text-[0.7rem] font-medium text-primary">
            feeds next run
          </span>
        </div>
      </div>
    </div>
  );
}

function LoopNode({
  step,
  i,
}: {
  step: (typeof LOOP)[number];
  i: number;
}) {
  const Icon = step.icon;
  return (
    <div className="flex w-[116px] shrink-0 flex-col items-center gap-2 text-center">
      <span
        className="fb-node flex size-12 items-center justify-center rounded-xl border border-border bg-secondary text-muted-foreground"
        style={{ animationDelay: `${i * 1.2}s` }}
      >
        <Icon className="size-5" />
      </span>
      <div>
        <div className="text-sm font-semibold text-foreground">{step.title}</div>
        <div className="text-[0.7rem] leading-tight text-muted-foreground">
          {step.sub}
        </div>
      </div>
    </div>
  );
}

function LoopConnector() {
  return (
    <div className="relative mt-6 h-0.5 w-8 shrink-0 rounded-full fb-flow sm:w-12" aria-hidden>
      <span className="absolute -right-0.5 -top-[3px] size-2 rotate-45 border-r-2 border-t-2 border-primary/60" />
    </div>
  );
}

const TINT: Record<string, { chip: string; icon: string }> = {
  warning: { chip: "bg-warning/10", icon: "text-warning" },
  destructive: { chip: "bg-destructive/10", icon: "text-destructive" },
  primary: { chip: "bg-primary/10", icon: "text-primary" },
};

function ProblemCard({
  icon,
  title,
  kicker,
  tint = "primary",
  children,
}: {
  icon: React.ReactNode;
  title: string;
  kicker: string;
  tint?: keyof typeof TINT;
  children: React.ReactNode;
}) {
  const t = TINT[tint];
  return (
    <div className="rounded-xl border border-border bg-card p-6 shadow-sm">
      <div className="flex items-center gap-3">
        <span
          className={`flex size-10 items-center justify-center rounded-lg ${t.chip} ${t.icon}`}
        >
          {icon}
        </span>
        <div>
          <p className="text-base font-semibold text-foreground">{title}</p>
          <p className="text-xs uppercase tracking-wider text-muted-foreground">
            {kicker}
          </p>
        </div>
      </div>
      <p className="mt-4 text-sm leading-relaxed text-muted-foreground">
        {children}
      </p>
    </div>
  );
}

function ExampleVoice({
  kicker,
  line,
  verdict,
  score,
}: {
  kicker: string;
  line: string;
  verdict: "pass" | "fail";
  score: string;
}) {
  const pass = verdict === "pass";
  return (
    <div className="rounded-xl border border-border bg-background p-5">
      <p className="text-xs uppercase tracking-wider text-muted-foreground">
        {kicker}
      </p>
      <p className="mt-2 text-sm leading-relaxed text-foreground">{line}</p>
      <p
        className={`mt-4 text-2xl font-bold tabular-nums ${
          pass ? "text-success" : "text-destructive"
        }`}
      >
        {score}
      </p>
    </div>
  );
}

function StepCard({
  n,
  icon,
  title,
  where,
  children,
}: {
  n: number;
  icon: React.ReactNode;
  title: string;
  where: string;
  children: React.ReactNode;
}) {
  return (
    <div className="relative rounded-xl border border-border bg-card p-5 shadow-sm">
      <span className="absolute right-4 top-4 text-2xl font-bold tabular-nums text-primary/20">
        {n}
      </span>
      <span className="flex size-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
        {icon}
      </span>
      <p className="mt-3 text-base font-semibold text-foreground">{title}</p>
      <p className="text-[0.7rem] font-medium uppercase tracking-wider text-primary">
        {where}
      </p>
      <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
        {children}
      </p>
    </div>
  );
}

const USE_CASES: {
  icon: typeof Briefcase;
  title: string;
  body: string;
  outcome: string;
}[] = [
  {
    icon: Briefcase,
    title: "Recruiting phone screens",
    body: "An AI voice agent screens candidates for a role. FairBench pushes the same strong, structured answer through the screen under many accents and names — and catches candidates failing because the transcriber dropped a key word, or being under-scored by the judge purely by name.",
    outcome:
      "A phone screen is a legal hiring step. A group passing under 80% as often is bias you'd have to defend — caught before it's a liability.",
  },
  {
    icon: Pill,
    title: "Pharmacy & clinical skills",
    body: "A pharmacy tech handles a confused medication pickup. FairBench replays the same safe response — verify identity, explain the interaction, loop in the pharmacist — across accents and names, and separates a mis-heard word from a judge that under-credits the identical script by name.",
    outcome:
      "Failing a competent tech over an accent is both a fairness and a patient-safety problem. FairBench proves the score reflects the answer, not the voice.",
  },
  {
    icon: Stethoscope,
    title: "Nursing & licensure checks",
    body: "A nurse escalates a deteriorating patient. FairBench replays the same urgent, correct hand-off across demographic variants and shows whether a missed step is the transcriber mishearing an accent or the grader discounting the nurse.",
    outcome:
      "When the same competent escalation passes for some and fails for others, the assessment is broken — not the nurse. FairBench makes the grade defensible.",
  },
];

function UseCaseCard({
  icon,
  title,
  body,
  outcome,
}: (typeof USE_CASES)[number]) {
  const Icon = icon;
  return (
    <div className="flex flex-col rounded-xl border border-border bg-card p-6 shadow-sm">
      <span className="flex size-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
        <Icon className="size-5" />
      </span>
      <p className="mt-3 text-base font-semibold text-foreground">{title}</p>
      <p className="mt-2 flex-1 text-sm leading-relaxed text-muted-foreground">
        {body}
      </p>
      <p className="mt-4 border-t border-border pt-3 text-sm leading-relaxed text-foreground">
        <span className="font-semibold text-primary">So what · </span>
        {outcome}
      </p>
    </div>
  );
}
