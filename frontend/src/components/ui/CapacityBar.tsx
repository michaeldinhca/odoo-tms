import { cn } from "./cn";

export type CapacityStatus = "ok" | "warning" | "full";

interface CapacityBarProps {
  value: number;
  max: number;
  label?: string;
  className?: string;
}

const FILL_CLASSES: Record<CapacityStatus, string> = {
  ok: "bg-status-ok",
  warning: "bg-status-warning",
  full: "bg-status-full",
};

function statusForRatio(ratio: number): CapacityStatus {
  if (ratio >= 1) return "full";
  if (ratio >= 0.85) return "warning";
  return "ok";
}

/** Horizontal capacity/progress bar — first-class component, used
 * constantly in the load planner for vehicle fill level. `value`/`max`
 * share a unit (kg, m3, item count, ...); the caller decides which. */
export function CapacityBar({ value, max, label, className }: CapacityBarProps) {
  const ratio = max > 0 ? value / max : 0;
  const percent = Math.round(Math.min(ratio, 1) * 100);
  const status = statusForRatio(ratio);

  return (
    <div className={cn("flex flex-col gap-1", className)}>
      {label && (
        <div className="flex items-center justify-between text-xs font-medium uppercase tracking-wide text-text-muted">
          <span>{label}</span>
          <span>{percent}%</span>
        </div>
      )}
      <div
        className="h-2 w-full overflow-hidden rounded-md bg-bg"
        role="progressbar"
        aria-valuenow={percent}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={label}
      >
        <div
          className={cn(
            "h-full rounded-md transition-[width] motion-reduce:transition-none",
            FILL_CLASSES[status],
          )}
          style={{ width: `${percent}%` }}
        />
      </div>
    </div>
  );
}
