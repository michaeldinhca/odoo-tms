import { ROUTE_COLOR_PALETTE } from "../lib/routeColors";
import { cn } from "./ui/cn";

interface ColorSwatchPickerProps {
  value: string;
  onChange: (color: string) => void;
  label?: string;
}

/** A fixed row of clickable color circles, not a full-spectrum picker —
 * replaces the native `<input type="color">` (which opens the browser's
 * own RGB/hue picker) for route colors specifically, since routes should
 * only ever use one of the 12 palette colors, not an arbitrary hex. */
export function ColorSwatchPicker({ value, onChange, label }: ColorSwatchPickerProps) {
  return (
    <div className="flex flex-col gap-1">
      {label && (
        <span className="text-xs font-medium uppercase tracking-wide text-text-muted">{label}</span>
      )}
      <div className="flex flex-wrap gap-2">
        {ROUTE_COLOR_PALETTE.map((color) => (
          <button
            key={color}
            type="button"
            onClick={() => onChange(color)}
            aria-label={`Choose color ${color}`}
            aria-pressed={value === color}
            title={color}
            className={cn(
              "h-7 w-7 rounded-full border-2 transition-transform motion-reduce:transition-none",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2",
              value === color
                ? "scale-110 border-text"
                : "border-transparent hover:scale-105",
            )}
            style={{ backgroundColor: color }}
          />
        ))}
      </div>
    </div>
  );
}
