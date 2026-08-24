import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { useAuth } from "../lib/auth";
import { api } from "../lib/api";
import type { Page } from "../lib/types";
import type { Ticket, TicketSummary } from "../lib/tickets";
import { formatRelative } from "../lib/tickets";
import { PriorityBadge, StatusBadge } from "../components/ui";

function greeting(): string {
  const hour = new Date().getHours();
  if (hour < 12) return "Good morning";
  if (hour < 17) return "Good afternoon";
  return "Good evening";
}

export function DashboardPage() {
  const { user, hasPermission } = useAuth();
  const canSeeQueue = hasPermission("ticket.view_all");
  const summary = useQuery({
    queryKey: ["ticket-summary"],
    queryFn: async () => (await api.get<TicketSummary>("/api/v1/tickets/summary")).data,
  });
  const mine = useQuery({
    queryKey: ["tickets", "mine", user?.id],
    queryFn: async () =>
      (
        await api.get<Page<Ticket>>("/api/v1/tickets", {
          params: { requester_id: user?.id, limit: 6, sort: "updated_at" },
        })
      ).data,
    enabled: Boolean(user?.id),
  });

  return (
    <div className="space-y-6">
      <section className="hero-banner">
        <p className="text-sm text-white/80">{greeting()}</p>
        <h2 className="mt-1 text-2xl font-semibold tracking-tight">Welcome back, {user?.full_name}</h2>
        <p className="mt-1 max-w-xl text-sm text-white/80">
          {canSeeQueue
            ? "See what needs attention, assign work, and keep the queue moving."
            : "Track your requests and follow updates from IT."}
        </p>
      </section>
      <div className={`grid gap-4 ${canSeeQueue ? "md:grid-cols-3" : "md:grid-cols-2"}`}>
        <Link to="/profile" className="stat-card card p-4">
          <p className="text-xs uppercase tracking-wide text-muted">Department</p>
          <p className="mt-1 text-lg font-semibold">{user?.department?.name ?? "Unassigned"}</p>
        </Link>
        <Link to="/tickets" className="stat-card card p-4">
          <p className="text-xs uppercase tracking-wide text-muted">My tickets</p>
          <p className="mt-1 text-2xl font-semibold">{summary.data?.my_tickets ?? "—"}</p>
          <p className="mt-1 text-xs text-muted">{summary.data?.open_mine ?? 0} still open</p>
        </Link>
        {canSeeQueue && (
          <Link to="/agent/my-queue" className="stat-card card p-4">
            <p className="text-xs uppercase tracking-wide text-muted">Assigned to me</p>
            <p className="mt-1 text-2xl font-semibold">{summary.data?.assigned_to_me ?? "—"}</p>
            <p className="mt-1 text-xs text-muted">{summary.data?.unassigned ?? 0} unassigned</p>
          </Link>
        )}
      </div>
      <div className="flex flex-wrap gap-3 text-sm">
        <Link className="btn-primary" to="/tickets/new">
          New ticket
        </Link>
        <Link className="btn-secondary" to="/tickets">
          View my tickets
        </Link>
        {canSeeQueue && (
          <Link className="btn-secondary" to="/agent/unassigned">
            Unassigned queue
          </Link>
        )}
      </div>
      <div>
        <div className="mb-3 flex items-center justify-between">
          <h3 className="text-sm font-semibold">Recently updated</h3>
          <Link className="btn-ghost text-xs" to="/tickets">
            See all
          </Link>
        </div>
        {mine.isLoading && <p className="text-sm text-muted">Loading tickets…</p>}
        {mine.data && mine.data.items.length === 0 && (
          <div className="empty-state">
            <p className="font-semibold">No tickets yet</p>
            <p className="mt-1 text-sm text-muted">Open a request and IT will pick it up from here.</p>
            <Link className="btn-primary mt-4" to="/tickets/new">
              Create a ticket
            </Link>
          </div>
        )}
        <div className="grid gap-3">
          {mine.data?.items.map((ticket) => (
            <Link key={ticket.id} to={`/tickets/${ticket.id}`} className="ticket-card">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="font-mono text-[11px] text-muted">{ticket.ticket_number}</p>
                  <p className="mt-0.5 truncate font-medium">{ticket.title}</p>
                </div>
                <p className="whitespace-nowrap text-xs text-muted">{formatRelative(ticket.updated_at)}</p>
              </div>
              <div className="mt-3 flex flex-wrap items-center gap-2">
                <StatusBadge status={ticket.status} />
                <PriorityBadge priority={ticket.priority} />
                <span className="text-xs text-muted">
                  {ticket.assigned_agent?.full_name ?? "Waiting for assignment"}
                </span>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
