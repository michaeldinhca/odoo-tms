import type { InputHTMLAttributes } from "react";
import { cn } from "./cn";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
}

const FIELD_CLASSES = cn(
  "rounded-md border border-border bg-surface px-3 py-2 text-sm text-text placeholder:text-text-muted",
  "transition-colors motion-reduce:transition-none",
  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:border-accent",
  "disabled:cursor-not-allowed disabled:opacity-50",
);

export function Input({ label, className, ...props }: InputProps) {
  const input = <input className={cn(FIELD_CLASSES, className)} {...props} />;

  if (!label) return input;

  return (
    <label className="flex flex-col gap-1">
      <span className="text-xs font-medium uppercase tracking-wide text-text-muted">{label}</span>
      {input}
    </label>
  );
}
