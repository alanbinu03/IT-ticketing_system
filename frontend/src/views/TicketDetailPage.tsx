import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useParams } from "react-router-dom";
import { useState } from "react";
import { api, getErrorMessage } from "../lib/api";
import { useAuth } from "../lib/auth";
import type { Page, User } from "../lib/types";
import type { Ticket, TimelineEvent } from "../lib/tickets";
import { VISIBLE_TRANSITIONS, formatDate, formatRelative, statusLabel, visibleStatus } from "../lib/tickets";
import { Avatar, BackLink, PriorityBadge, PromptOption, StatusBadge } from "../components/ui";

export function TicketDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { user, hasPermission } = useAuth();
  const queryClient = useQueryClient();
  const [comment, setComment] = useState("");
  const [internal, setInternal] = useState(false);
  const [error, setError] = useState<string | null>(null);
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
      });
    },
    onSuccess: async () => {
      setError(null);
      await refresh();
    },
    onError: (err) => setError(getErrorMessage(err)),
  });

  const assign = useMutation({
    mutationFn: async (payload?: { agent_id?: string | null }) => {
      const agentId = payload && "agent_id" in payload ? payload.agent_id : assigneeId || null;
      await api.post(`/api/v1/tickets/${id}/assign`, {
        agent_id: agentId,
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

  const currentVisible = visibleStatus(ticket.status);
  const nextVisible =
    currentVisible === "CANCELLED" || currentVisible === "REJECTED"
      ? []
      : VISIBLE_TRANSITIONS[currentVisible].filter((status) => {
          if (status === "RESOLVED") return hasPermission("ticket.resolve");
          if (status === "IN_PROGRESS" && ticket.status === "CLOSED") return false;
          if (status === "IN_PROGRESS" && ticket.status === "RESOLVED") {
            return hasPermission("ticket.reopen");
          }
          return hasPermission("ticket.update");
        });
  const canComplete = nextVisible.includes("RESOLVED");
  const moveStatuses = nextVisible.filter((status) => status !== "RESOLVED");
  const isFinished = currentVisible === "RESOLVED" || currentVisible === "CANCELLED" || currentVisible === "REJECTED";
  const canAssign = hasPermission("ticket.assign") && !ticket.assigned_agent && !isFinished;
  const canRelease =
    Boolean(ticket.assigned_agent) &&
    !isFinished &&
    (hasPermission("ticket.reassign") || hasPermission("ticket.assign"));

  return (
    <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_18rem]">
      <div className="space-y-4">
        <div className="card p-5">
          <BackLink to="/tickets">← Back to tickets</BackLink>
          <p className="mt-4 font-mono text-xs text-muted">{ticket.ticket_number}</p>
          <div className="mt-1 flex flex-wrap items-center gap-2">
            <h2 className="text-xl font-semibold leading-7 tracking-tight">{ticket.title}</h2>
            <StatusBadge status={ticket.status} />
            <PriorityBadge priority={ticket.priority} />
          </div>
          <p className="mt-4 whitespace-pre-wrap text-sm leading-6 text-ink">{ticket.description}</p>
        </div>
        <div className="space-y-3">
          {(timelineQuery.data ?? []).length === 0 && (
            <p className="text-sm text-muted">No activity yet. Add a comment to start the thread.</p>
          )}
          {(timelineQuery.data ?? []).map((event) => (
            <div
              key={event.id}
              className={`flex gap-3 rounded-2xl border p-4 text-sm ${
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
            className="card space-y-4 p-5"
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
                <label className="inline-flex items-center gap-2 text-sm text-muted">
                  <input
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
      <aside className="lg:sticky lg:top-0">
        <div className="card overflow-hidden">
          <div className="space-y-4 border-b border-edge p-5 text-sm">
            <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted">Details</p>
            <Meta label="Requester" value={ticket.requester?.full_name} />
            <Meta label="Category" value={ticket.subcategory?.name ?? ticket.category?.name ?? "—"} />
            <Meta label="Assigned to" value={ticket.assigned_agent?.full_name ?? "Unassigned"} />
            <Meta label="Created" value={formatDate(ticket.created_at)} />
            {ticket.resolution_summary && <Meta label="Resolution" value={ticket.resolution_summary} />}
          </div>
          {canComplete && (
            <div className="space-y-2 border-b border-edge p-5">
              <button
                className="btn-primary w-full"
                type="button"
                disabled={changeStatus.isPending}
                onClick={() => changeStatus.mutate("RESOLVED")}
              >
                {changeStatus.isPending ? "Saving…" : "Mark resolved"}
              </button>
            </div>
          )}
          {canAssign && (
            <div className="space-y-3 border-b border-edge p-5">
              <p className="text-sm font-medium">Assign to</p>
              <select className="input" value={assigneeId} onChange={(e) => setAssigneeId(e.target.value)}>
                <PromptOption label="Select admin" />
                {(users.data?.items ?? [])
                  .filter((item) => item.roles.includes("Admin"))
                  .map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.full_name}
                    </option>
                  ))}
              </select>
              <button
                className="btn-secondary w-full"
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
          {canRelease && (
            <div className="space-y-3 border-b border-edge p-5">
              <p className="text-sm font-medium">Assignment</p>
              <p className="text-sm leading-6 text-muted">
                This ticket is assigned to {ticket.assigned_agent?.full_name}. Return it to the unassigned
                queue if you will not take it.
              </p>
              <button
                className="btn-secondary w-full"
                type="button"
                disabled={assign.isPending}
                onClick={() => assign.mutate({ agent_id: null })}
              >
                {assign.isPending ? "Saving…" : "Return to unassigned"}
              </button>
            </div>
          )}
          {moveStatuses.length > 0 && (
            <div className="p-5">
              <p className="text-sm font-medium">Status</p>
              <div className="mt-3 flex flex-wrap gap-2">
                {moveStatuses.map((status) => (
                  <button
                    key={status}
                    className="btn-secondary text-xs"
                    type="button"
                    disabled={changeStatus.isPending}
                    onClick={() => changeStatus.mutate(status)}
                  >
                    {statusLabel(status)}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
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
