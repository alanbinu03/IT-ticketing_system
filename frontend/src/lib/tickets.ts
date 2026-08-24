export type TicketPriority = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";
export type TicketSeverity = TicketPriority;
export type TicketStatus =
  | "NEW"
  | "OPEN"
  | "ASSIGNED"
  | "IN_PROGRESS"
  | "WAITING_FOR_USER"
  | "WAITING_FOR_VENDOR"
  | "ON_HOLD"
  | "RESOLVED"
  | "CLOSED"
  | "CANCELLED"
  | "REJECTED"
  | "REOPENED";

export type UserRef = {
  id: string;
  full_name: string;
  email: string;
};

export type NamedRef = {
  id: string;
  name: string;
  code?: string | null;
};

export type Ticket = {
  id: string;
  ticket_number: string;
  title: string;
  description: string;
  requester: UserRef | null;
  department: NamedRef | null;
  assigned_team: NamedRef | null;
  assigned_agent: UserRef | null;
  category: NamedRef | null;
  subcategory: NamedRef | null;
  priority: TicketPriority;
  severity: TicketSeverity;
  status: TicketStatus;
  source: string;
  assigned_at: string | null;
  first_response_at: string | null;
  resolved_at: string | null;
  closed_at: string | null;
  due_at: string | null;
  resolution_summary: string | null;
  tags: string[];
  version: number;
  created_at: string;
  updated_at: string;
};

export type Category = {
  id: string;
  name: string;
  parent_id: string | null;
  is_active: boolean;
  description: string | null;
  children: Category[];
};

export type TimelineEvent = {
  id: string;
  type: string;
  at: string;
  actor: UserRef | null;
  summary: string;
  body: string | null;
  comment_type: string | null;
  metadata?: Record<string, string | null> | null;
};

export const PRIORITY_LABEL: Record<TicketPriority, string> = {
  CRITICAL: "P1",
  HIGH: "P2",
  MEDIUM: "P3",
  LOW: "P4",
};

export const STATUS_TRANSITIONS: Record<TicketStatus, TicketStatus[]> = {
  NEW: ["OPEN", "ASSIGNED", "CANCELLED", "REJECTED"],
  OPEN: ["ASSIGNED", "IN_PROGRESS", "CANCELLED", "REJECTED"],
  ASSIGNED: ["IN_PROGRESS", "OPEN", "CANCELLED"],
  IN_PROGRESS: ["WAITING_FOR_USER", "WAITING_FOR_VENDOR", "ON_HOLD", "RESOLVED"],
  WAITING_FOR_USER: ["IN_PROGRESS", "ON_HOLD", "RESOLVED"],
  WAITING_FOR_VENDOR: ["IN_PROGRESS", "ON_HOLD"],
  ON_HOLD: ["IN_PROGRESS"],
  RESOLVED: ["CLOSED", "REOPENED"],
  REOPENED: ["ASSIGNED", "IN_PROGRESS"],
  CLOSED: [],
  CANCELLED: [],
  REJECTED: [],
};

export function priorityClass(priority: TicketPriority): string {
  if (priority === "CRITICAL") return "badge-p1";
  if (priority === "HIGH") return "badge-p2";
  if (priority === "MEDIUM") return "badge-p3";
  return "badge-p4";
}

export function statusClass(status: TicketStatus): string {
  if (status === "NEW" || status === "OPEN") return "badge-new";
  if (status === "ASSIGNED" || status === "IN_PROGRESS") return "badge-work";
  if (status === "WAITING_FOR_USER" || status === "WAITING_FOR_VENDOR" || status === "ON_HOLD") {
    return "badge-wait";
  }
  if (status === "RESOLVED") return "badge-done";
  if (status === "CLOSED") return "badge-closed";
  if (status === "CANCELLED" || status === "REJECTED") return "badge-stop";
  return "badge-reopen";
}

export function formatDate(value: string | null): string {
  if (!value) return "—";
  return new Date(value).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

export function formatRelative(value: string | null): string {
  if (!value) return "—";
  const then = new Date(value).getTime();
  const delta = Math.round((then - Date.now()) / 1000);
  const abs = Math.abs(delta);
  const rtf = new Intl.RelativeTimeFormat(undefined, { numeric: "auto" });
  if (abs < 60) return rtf.format(Math.round(delta), "second");
  if (abs < 3600) return rtf.format(Math.round(delta / 60), "minute");
  if (abs < 86400) return rtf.format(Math.round(delta / 3600), "hour");
  if (abs < 604800) return rtf.format(Math.round(delta / 86400), "day");
  return formatDate(value);
}

export type TicketSummary = {
  my_tickets: number;
  open_mine: number;
  assigned_to_me: number | null;
  unassigned: number | null;
};
