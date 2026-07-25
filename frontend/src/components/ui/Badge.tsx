import type { HTMLAttributes } from "react";
import { cn } from "./cn";

export type BadgeVariant = "neutral" | "accent" | "ok" | "warning" | "full";

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant;
}

const VARIANT_CLASSES: Record<BadgeVariant, string> = {
  neutral: "border-border bg-bg text-text-muted",
  accent: "border-accent/30 bg-accent/10 text-accent",
  ok: "border-status-ok/30 bg-status-ok/10 text-status-ok",
  warning: "border-status-warning/30 bg-status-warning/10 text-status-warning",
  full: "border-status-full/30 bg-status-full/10 text-status-full",
};

/** Status badge/pill — for connection state, sync/link status, capacity
 * status, etc. Deliberately the same radius token as everything else
 * (rounded-md, not fully rounded) — see design.md. */
export function Badge({ variant = "neutral", className, children, ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-md border px-2 py-0.5 text-xs font-medium uppercase tracking-wide",
        VARIANT_CLASSES[variant],
        className,
      )}
      {...props}
    >
      {children}
    </span>
  );
}
