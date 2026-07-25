import type { SelectHTMLAttributes } from "react";
import { cn } from "./cn";

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
}

const FIELD_CLASSES = cn(
  "rounded-md border border-border bg-surface px-3 py-2 text-sm text-text",
  "transition-colors motion-reduce:transition-none",
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:border-accent",
  "disabled:cursor-not-allowed disabled:opacity-50",
);

export function Select({ label, className, children, ...props }: SelectProps) {
  const select = (
    <select className={cn(FIELD_CLASSES, className)} {...props}>
      {children}
    </select>
  );

  if (!label) return select;

  return (
    <label className="flex flex-col gap-1">
      <span className="text-xs font-medium uppercase tracking-wide text-text-muted">{label}</span>
      {select}
    </label>
  );
}
