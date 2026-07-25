import type { HTMLAttributes, ReactNode } from "react";
import { cn } from "./cn";

interface CardProps extends Omit<HTMLAttributes<HTMLDivElement>, "title"> {
  heading?: ReactNode;
}

/** Basis for panels, vehicle boxes, and cluster groups in later phases —
 * a plain padded, bordered, elevated surface. */
export function Card({ heading, className, children, ...props }: CardProps) {
  return (
    <div className={cn("rounded-md border border-border bg-surface p-4 shadow-sm", className)} {...props}>
      {heading && <h2 className="mb-3 text-lg font-semibold text-text">{heading}</h2>}
      {children}
    </div>
  );
}
