import { forwardRef } from "react";
import type { HTMLAttributes, ReactNode } from "react";
import { cn } from "./cn";

interface CardProps extends Omit<HTMLAttributes<HTMLDivElement>, "title"> {
  heading?: ReactNode;
}

/** Basis for panels, vehicle boxes, and cluster groups in later phases —
 * a plain padded, bordered, elevated surface. Forwards its ref so it
 * composes with things that need the underlying DOM node directly (e.g.
 * dnd-kit's `useDroppable`/`useDraggable`). */
export const Card = forwardRef<HTMLDivElement, CardProps>(function Card(
  { heading, className, children, ...props },
  ref,
) {
  return (
    <div
      ref={ref}
      className={cn("rounded-md border border-border bg-surface p-4 shadow-sm", className)}
      {...props}
    >
      {heading && <h2 className="mb-3 text-lg font-semibold text-text">{heading}</h2>}
      {children}
    </div>
  );
});
