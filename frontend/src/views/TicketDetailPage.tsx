import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams } from "react-router-dom";
import { useState } from "react";
import { api, getErrorMessage } from "../lib/api";
import { useAuth } from "../lib/auth";
import type { Page, User } from "../lib/types";
import type { Ticket, TimelineEvent } from "../lib/tickets";
import { STATUS_TRANSITIONS, formatDate, formatRelative } from "../lib/tickets";
import { Avatar, BackLink, PriorityBadge, StatusBadge } from "../components/ui";

export function TicketDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { user, hasPermission } = useAuth();
  const queryClient = useQueryClient();
  const [comment, setComment] = useState("");
  const [internal, setInternal] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [resolution, setResolution] = useState("");
  const [assigneeId, setAssigneeId] = useState("");

  const ticketQuery = useQuery({
    queryKey: ["ticket", id],
    queryFn: async () => (await api.get<Ticket>(`/api/v1/tickets/${id}`)).data,
    enabled: Boolean(id),
  });
  const timelineQuery = useQuery({
    queryKey: ["ticket-timeline", id],
    queryFn: async () => (await api.get<TimelineEvent[]>(`/api/v1/tickets/${id}/timeline`)).data,
    enabled: Boolean(id),
  });
  const users = useQuery({
    queryKey: ["users"],
    queryFn: async () =>
      (await api.get<Page<User>>("/api/v1/users", { params: { limit: 100, is_active: true } })).data,
    enabled: hasPermission("ticket.assign"),
  });

  const refresh = async () => {
    await queryClient.invalidateQueries({ queryKey: ["ticket", id] });
    await queryClient.invalidateQueries({ queryKey: ["ticket-timeline", id] });
    await queryClient.invalidateQueries({ queryKey: ["tickets"] });
    await queryClient.invalidateQueries({ queryKey: ["ticket-summary"] });
  };

  const addComment = useMutation({
    mutationFn: async () => {
      await api.post(`/api/v1/tickets/${id}/comments`, {
        body: comment,
        type: internal ? "INTERNAL_NOTE" : "PUBLIC_COMMENT",
      });
    },
    onSuccess: async () => {
      setComment("");
      setError(null);
      await refresh();
    },
    onError: (err) => setError(getErrorMessage(err)),
  });

  const changeStatus = useMutation({
    mutationFn: async (status: string) => {
      await api.post(`/api/v1/tickets/${id}/status`, {
        status,
        version: ticketQuery.data?.version,
        resolution_summary: status === "RESOLVED" ? resolution : undefined,
      });
    },
    onSuccess: async () => {
      setError(null);
      await refresh();
    },
    onError: (err) => setError(getErrorMessage(err)),
  });

  const assign = useMutation({
    mutationFn: async (payload?: { agent_id?: string }) => {
      await api.post(`/api/v1/tickets/${id}/assign`, {
        agent_id: payload?.agent_id ?? (assigneeId || null),
        version: ticketQuery.data?.version,
      });
    },
    onSuccess: async () => {
      setError(null);
      await refresh();
    },
    onError: (err) => setError(getErrorMessage(err)),
  });

  const ticket = ticketQuery.data;
  if (ticketQuery.isLoading) {
    return <p className="text-sm text-muted">Loading ticket…</p>;
  }
  if (!ticket) {
    return (
      <div className="empty-state">
        <p className="font-semibold">This ticket could not be found</p>
        <BackLink to="/tickets">Back to tickets</BackLink>
      </div>
    );
  }

  const nextStatuses = STATUS_TRANSITIONS[ticket.status].filter((status) => {
    if (status === "RESOLVED") return hasPermission("ticket.resolve");
    if (status === "CLOSED") return hasPermission("ticket.close");
    if (status === "REOPENED") return hasPermission("ticket.reopen");
    return hasPermission("ticket.update");
  });
  const canCloseTicket = ticket.status === "RESOLVED" && nextStatuses.includes("CLOSED");
  const moveStatuses = nextStatuses.filter((status) => status !== "CLOSED");

  return (
    <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
      <div className="space-y-4">
        <div>
          <BackLink to="/tickets">← Back to tickets</BackLink>
          <p className="mt-3 font-mono text-xs text-muted">{ticket.ticket_number}</p>
          <div className="mt-1 flex flex-wrap items-center gap-2">
            <h2 className="text-2xl font-semibold tracking-tight">{ticket.title}</h2>
            <StatusBadge status={ticket.status} />
            <PriorityBadge priority={ticket.priority} />
          </div>
          <p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-ink">{ticket.description}</p>
        </div>
        <div className="space-y-3">
          {(timelineQuery.data ?? []).length === 0 && (
            <p className="text-sm text-muted">No activity yet. Add a comment to start the thread.</p>
          )}
          {(timelineQuery.data ?? []).map((event) => (
            <div
              key={event.id}
              className={`flex gap-3 rounded-2xl border p-3 text-sm ${
                event.comment_type === "INTERNAL_NOTE"
                  ? "border-amber-400/50 bg-amber-500/10"
                  : "border-edge bg-surface"
              }`}
            >
              <Avatar name={event.actor?.full_name ?? "System"} size="sm" />
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-muted">
                  <span>
                    <span className="font-medium text-ink">{event.actor?.full_name ?? "System"}</span>
                    {" · "}
                    {event.summary}
                    {event.comment_type === "INTERNAL_NOTE" ? " · Internal" : ""}
                  </span>
                  <span title={formatDate(event.at)}>{formatRelative(event.at)}</span>
                </div>
                {event.body && <p className="mt-2 whitespace-pre-wrap leading-6">{event.body}</p>}
              </div>
            </div>
          ))}
        </div>
        {hasPermission("ticket.comment") && (
          <form
            className="card space-y-3 p-4"
            onSubmit={(e) => {
              e.preventDefault();
              if (comment.trim()) addComment.mutate();
            }}
          >
            <textarea
              className="input"
              placeholder={internal ? "Internal note (not visible to the requester)" : "Write a reply…"}
              rows={4}
              value={comment}
              onChange={(e) => setComment(e.target.value)}
            />
            <div className="flex items-center justify-between gap-3">
              {hasPermission("ticket.internal_note") ? (
                <label className="text-sm text-muted">
                  <input
                    className="mr-2"
                    type="checkbox"
                    checked={internal}
                    onChange={(e) => setInternal(e.target.checked)}
                  />
                  Internal note
                </label>
              ) : (
                <span />
              )}
              <button className="btn-primary" type="submit" disabled={addComment.isPending || !comment.trim()}>
                {addComment.isPending ? "Posting…" : "Post reply"}
              </button>
            </div>
          </form>
        )}
        {error && <p className="text-sm text-red-500">{error}</p>}
      </div>
      <aside className="space-y-4 lg:sticky lg:top-0">
        <div className="card space-y-3 p-4 text-sm">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted">Details</p>
          <Meta label="Requester" value={ticket.requester?.full_name} />
          <Meta label="Category" value={ticket.subcategory?.name ?? ticket.category?.name ?? "—"} />
          <Meta label="Team" value={ticket.assigned_team?.name ?? "Unassigned"} />
          <Meta label="Agent" value={ticket.assigned_agent?.full_name ?? "Unassigned"} />
          <Meta label="Created" value={formatDate(ticket.created_at)} />
          {ticket.resolution_summary && <Meta label="Resolution" value={ticket.resolution_summary} />}
        </div>
        {canCloseTicket && (
          <div className="card space-y-2 p-4">
            <p className="text-sm font-medium">Completed</p>
            <p className="text-sm text-muted">This ticket is resolved. Close it when the work is confirmed done.</p>
            <button
              className="btn-primary w-full"
              type="button"
              disabled={changeStatus.isPending}
              onClick={() => changeStatus.mutate("CLOSED")}
            >
              {changeStatus.isPending ? "Closing…" : "Close ticket"}
            </button>
          </div>
        )}
        {moveStatuses.length > 0 && (
          <div className="card space-y-2 p-4">
            <p className="text-sm font-medium">Move this ticket</p>
            {moveStatuses.includes("RESOLVED") && (
              <textarea
                className="input"
                placeholder="Resolution summary (required to resolve)"
                value={resolution}
                onChange={(e) => setResolution(e.target.value)}
              />
            )}
            <div className="flex flex-wrap gap-2">
              {moveStatuses.map((status) => (
                <button
                  key={status}
                  className="btn-secondary text-xs"
                  type="button"
                  disabled={changeStatus.isPending || (status === "RESOLVED" && !resolution.trim())}
                  onClick={() => changeStatus.mutate(status)}
                >
                  {changeStatus.isPending ? "Updating…" : status.replaceAll("_", " ")}
                </button>
              ))}
            </div>
          </div>
        )}
        {hasPermission("ticket.assign") && (
          <div className="card space-y-2 p-4">
            <p className="text-sm font-medium">Assign to</p>
            <select className="input" value={assigneeId} onChange={(e) => setAssigneeId(e.target.value)}>
              <option value="">Select admin</option>
              {(users.data?.items ?? [])
                .filter((item) => item.roles.includes("Admin"))
                .map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.full_name}
                  </option>
                ))}
            </select>
            <button
              className="btn-primary w-full"
              type="button"
              disabled={assign.isPending || !assigneeId}
              onClick={() => assign.mutate({})}
            >
              {assign.isPending ? "Saving…" : "Save assignment"}
            </button>
            {user?.id && (
              <button
                className="btn-ghost"
                type="button"
                disabled={assign.isPending}
                onClick={() => {
                  setAssigneeId(user.id);
                  assign.mutate({ agent_id: user.id });
                }}
              >
                Assign to me
              </button>
            )}
          </div>
        )}
      </aside>
    </div>
  );
}

function Meta({ label, value }: { label: string; value?: string | null }) {
  return (
    <div>
      <p className="text-xs uppercase tracking-wide text-muted">{label}</p>
      <p className="mt-0.5 font-medium">{value ?? "—"}</p>
    </div>
  );
}
