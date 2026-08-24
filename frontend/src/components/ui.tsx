import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import type { TicketPriority, TicketStatus } from "../lib/tickets";
import { PRIORITY_LABEL, priorityClass, statusClass } from "../lib/tickets";

export function initials(name?: string | null): string {
  const parts = (name ?? "?").trim().split(/\s+/).filter(Boolean);
  return parts
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("");
}

export function Avatar({
  name,
  size = "md",
}: {
  name?: string | null;
  size?: "sm" | "md" | "lg";
}) {
  const sizes = {
    sm: "h-8 w-8 text-[11px]",
    md: "h-10 w-10 text-sm",
    lg: "h-14 w-14 text-lg",
  };
  return <span className={`avatar ${sizes[size]}`}>{initials(name)}</span>;
}

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  actions?: ReactNode;
}) {
  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
      <div>
        {eyebrow && <p className="text-xs font-medium uppercase tracking-[0.18em] text-muted">{eyebrow}</p>}
        <h2 className="mt-1 text-2xl font-semibold tracking-tight">{title}</h2>
        {description && <p className="mt-1 max-w-xl text-sm text-muted">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </div>
  );
}

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <div className="empty-state">
      <p className="text-base font-semibold">{title}</p>
      <p className="mt-1 text-sm text-muted">{description}</p>
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export function StatusBadge({ status }: { status: TicketStatus }) {
  return (
    <span className={`badge ${statusClass(status)}`}>{status.replaceAll("_", " ")}</span>
  );
}

export function PriorityBadge({ priority }: { priority: TicketPriority }) {
  return (
    <span className={`badge ${priorityClass(priority)}`}>
      {PRIORITY_LABEL[priority]} {priority.toLowerCase()}
    </span>
  );
}

export function BackLink({ to, children }: { to: string; children: ReactNode }) {
  return (
    <Link className="btn-ghost" to={to}>
      {children}
    </Link>
  );
}
