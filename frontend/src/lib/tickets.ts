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

export const VISIBLE_STATUSES = ["NEW", "IN_PROGRESS", "ON_HOLD", "RESOLVED"] as const;
export type VisibleStatus = (typeof VISIBLE_STATUSES)[number];

export const STATUS_GROUP: Record<VisibleStatus, TicketStatus[]> = {
  NEW: ["NEW", "OPEN", "REOPENED"],
  IN_PROGRESS: ["ASSIGNED", "IN_PROGRESS"],
  ON_HOLD: ["WAITING_FOR_USER", "WAITING_FOR_VENDOR", "ON_HOLD"],
  RESOLVED: ["RESOLVED", "CLOSED"],
};

export const VISIBLE_TRANSITIONS: Record<VisibleStatus, VisibleStatus[]> = {
  NEW: ["IN_PROGRESS", "ON_HOLD", "RESOLVED"],
  IN_PROGRESS: ["ON_HOLD", "RESOLVED"],
  ON_HOLD: ["IN_PROGRESS", "RESOLVED"],
  RESOLVED: ["IN_PROGRESS"],
};

export const STATUS_TRANSITIONS: Record<TicketStatus, TicketStatus[]> = {
  NEW: ["OPEN", "ASSIGNED", "IN_PROGRESS", "ON_HOLD", "CANCELLED", "REJECTED", "RESOLVED"],
  OPEN: ["ASSIGNED", "IN_PROGRESS", "ON_HOLD", "CANCELLED", "REJECTED", "RESOLVED"],
  ASSIGNED: ["IN_PROGRESS", "OPEN", "ON_HOLD", "CANCELLED", "RESOLVED"],
  IN_PROGRESS: ["WAITING_FOR_USER", "WAITING_FOR_VENDOR", "ON_HOLD", "RESOLVED"],
  WAITING_FOR_USER: ["IN_PROGRESS", "ON_HOLD", "RESOLVED"],
  WAITING_FOR_VENDOR: ["IN_PROGRESS", "ON_HOLD", "RESOLVED"],
  ON_HOLD: ["IN_PROGRESS", "RESOLVED"],
  RESOLVED: ["CLOSED", "REOPENED", "IN_PROGRESS"],
  REOPENED: ["ASSIGNED", "IN_PROGRESS", "ON_HOLD", "RESOLVED"],
  CLOSED: [],
  CANCELLED: [],
  REJECTED: [],
};

export function visibleStatus(status: TicketStatus): VisibleStatus | "CANCELLED" | "REJECTED" {
  if (status === "CANCELLED" || status === "REJECTED") return status;
  for (const item of VISIBLE_STATUSES) {
    if (STATUS_GROUP[item].includes(status)) return item;
  }
  return "NEW";
}

export function statusLabel(status: TicketStatus): string {
  const visible = visibleStatus(status);
  if (visible === "NEW") return "New";
  if (visible === "IN_PROGRESS") return "In progress";
  if (visible === "ON_HOLD") return "On hold";
  if (visible === "RESOLVED") return "Resolved";
  if (visible === "CANCELLED") return "Cancelled";
  return "Rejected";
}

export function statusClass(status: TicketStatus): string {
  const visible = visibleStatus(status);
  if (visible === "NEW") return "badge-new";
  if (visible === "IN_PROGRESS") return "badge-work";
  if (visible === "ON_HOLD") return "badge-wait";
  if (visible === "RESOLVED") return "badge-done";
  return "badge-stop";
}

export function priorityClass(priority: TicketPriority): string {
  if (priority === "CRITICAL") return "badge-p1";
  if (priority === "HIGH") return "badge-p2";
  if (priority === "MEDIUM") return "badge-p3";
  return "badge-p4";
}

export const ACTIVE_QUEUE_STATUSES: TicketStatus[] = [
  "NEW",
  "OPEN",
  "ASSIGNED",
  "IN_PROGRESS",
  "WAITING_FOR_USER",
  "WAITING_FOR_VENDOR",
  "ON_HOLD",
  "REOPENED",
];

export const COMPLETED_QUEUE_STATUSES: TicketStatus[] = ["RESOLVED", "CLOSED"];

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
