"use client";

import * as React from "react";
import { Info } from "lucide-react";

import { cn } from "@/lib/utils";

type Align = "center" | "start" | "end";

const ALIGN_CLASS: Record<Align, string> = {
  center: "left-1/2 -translate-x-1/2",
  start: "left-0",
  end: "right-0",
};

const POPOVER =
  "pointer-events-none absolute bottom-full z-50 mb-2 w-60 max-w-[min(16rem,70vw)] rounded-lg border border-border bg-card px-3 py-2 text-left text-xs font-normal leading-relaxed text-card-foreground opacity-0 shadow-lg transition-opacity duration-150 group-hover:opacity-100 group-focus-within:opacity-100";

/**
 * A small "info" affordance that reveals a plain-language explanation on hover
 * or keyboard focus. Used to decode domain jargon inline without cluttering the
 * primary copy. Keyboard-accessible (focusable button + group-focus-within).
 */
export function InfoTip({
  children,
  align = "center",
  label = "More information",
  className,
}: {
  children: React.ReactNode;
  align?: Align;
  label?: string;
  className?: string;
}) {
  return (
    <span className={cn("group relative inline-flex align-middle", className)}>
      <button
        type="button"
        aria-label={label}
        className="inline-flex size-4 items-center justify-center rounded-full text-muted-foreground/70 transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        <Info className="size-3.5" />
      </button>
      <span role="tooltip" className={cn(POPOVER, ALIGN_CLASS[align])}>
        {children}
      </span>
    </span>
  );
}

/**
 * Inline term with a dotted underline that reveals a definition on hover/focus.
 * Lets us keep plain headline copy while still defining the precise term for
 * users who want it.
 */
export function Term({
  children,
  tip,
  align = "center",
  className,
}: {
  children: React.ReactNode;
  tip: React.ReactNode;
  align?: Align;
  className?: string;
}) {
  return (
    <span
      tabIndex={0}
      className={cn(
        "group relative inline cursor-help underline decoration-dotted decoration-muted-foreground/50 underline-offset-[3px] focus-visible:outline-none",
        className,
      )}
    >
      {children}
      <span role="tooltip" className={cn(POPOVER, ALIGN_CLASS[align])}>
        {tip}
      </span>
    </span>
  );
}
