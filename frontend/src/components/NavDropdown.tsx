import { useEffect, useRef, useState } from "react";
import { NavLink, useLocation } from "react-router-dom";
import { cn } from "./ui/cn";

interface NavDropdownItem {
  to: string;
  label: string;
}

interface NavDropdownProps {
  label: string;
  items: NavDropdownItem[];
}

const TRIGGER_CLASSES = (active: boolean) =>
  cn(
    "flex items-center gap-1 rounded-md px-3 py-1.5 text-sm font-medium transition-colors motion-reduce:transition-none",
    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-surface",
    active ? "bg-accent/10 text-accent" : "text-text-muted hover:bg-bg hover:text-text",
  );

const ITEM_CLASSES = ({ isActive }: { isActive: boolean }) =>
  cn(
    "block rounded-sm px-3 py-1.5 text-sm transition-colors motion-reduce:transition-none",
    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent",
    isActive ? "bg-accent/10 text-accent" : "text-text hover:bg-bg",
  );

/** A grouped nav menu — trigger button + a panel of links, for grouping
 * related setup/config screens under one top-level slot instead of one
 * flat link per screen. Closes on an outside click, Escape (returning
 * focus to the trigger), or picking an item. No arrow-key roving focus —
 * Tab through items in DOM order, matching the accessibility floor used
 * elsewhere in this app (focus-visible ring, keyboard-operable, no full
 * ARIA authoring-practices menu implementation). */
export function NavDropdown({ label, items }: NavDropdownProps) {
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const location = useLocation();
  const active = items.some((item) => location.pathname.startsWith(item.to));

  useEffect(() => {
    setOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    if (!open) return;

    function handlePointerDown(event: MouseEvent) {
      if (!containerRef.current?.contains(event.target as Node)) setOpen(false);
    }
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setOpen(false);
        triggerRef.current?.focus();
      }
    }

    document.addEventListener("mousedown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("mousedown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [open]);

  return (
    <div ref={containerRef} className="relative">
      <button
        ref={triggerRef}
        type="button"
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen((prev) => !prev)}
        className={TRIGGER_CLASSES(active)}
      >
        {label}
        <svg
          viewBox="0 0 20 20"
          fill="currentColor"
          className={cn("h-4 w-4 transition-transform motion-reduce:transition-none", open && "rotate-180")}
          aria-hidden="true"
        >
          <path
            fillRule="evenodd"
            d="M5.23 7.21a.75.75 0 011.06.02L10 11.168l3.71-3.938a.75.75 0 111.08 1.04l-4.25 4.5a.75.75 0 01-1.08 0l-4.25-4.5a.75.75 0 01.02-1.06z"
            clipRule="evenodd"
          />
        </svg>
      </button>

      {open && (
        <div
          role="menu"
          className="absolute left-0 top-full z-20 mt-1 min-w-[190px] rounded-md border border-border bg-surface p-1 shadow-md"
        >
          {items.map((item) => (
            <NavLink key={item.to} to={item.to} role="menuitem" className={ITEM_CLASSES}>
              {item.label}
            </NavLink>
          ))}
        </div>
      )}
    </div>
  );
}
