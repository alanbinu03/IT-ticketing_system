import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "../lib/nav";
import { useEffect, useMemo, useState } from "react";
import { api, getErrorMessage } from "../lib/api";
import { useAuth } from "../lib/auth";
import type { Page, User } from "../lib/types";
import type { Ticket, TicketPriority, VisibleStatus } from "../lib/tickets";
import { STATUS_GROUP, VISIBLE_STATUSES, statusLabel } from "../lib/tickets";
import { PromptOption } from "../components/ui";
import { TicketTable } from "./TicketTable";

type Props = {
  title: string;
  description?: string;
  preset?: Record<string, string | boolean | string[] | undefined>;
  showCreate?: boolean;
  enableAssign?: boolean;
  enableUnassign?: boolean;
};

export function TicketsPage({
  preset,
  showCreate = true,
  enableAssign = true,
  enableUnassign = true,
}: Props) {
  const { hasPermission } = useAuth();
  const queryClient = useQueryClient();
  const [q, setQ] = useState("");
  const [debouncedQ, setDebouncedQ] = useState("");
  const [status, setStatus] = useState("");
  const [priority, setPriority] = useState("");
  const [sort, setSort] = useState("created_at");
  const [offset, setOffset] = useState(0);
  const [assignError, setAssignError] = useState<string | null>(null);
  const limit = 20;
  const canAssign = enableAssign && hasPermission("ticket.assign");
  const canUnassign =
    enableUnassign && (hasPermission("ticket.reassign") || hasPermission("ticket.assign"));

  useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedQ(q.trim()), 250);
    return () => window.clearTimeout(timer);
  }, [q]);

  const presetKey = JSON.stringify(preset ?? {});
  const presetStatus = Array.isArray(preset?.status) || typeof preset?.status === "string";
  const params = useMemo(() => {
    const parsed = JSON.parse(presetKey) as Record<string, string | boolean | number | string[]>;
    const next: Record<string, string | boolean | number | string[]> = {
      limit,
      offset,
      sort,
      order: "desc",
      ...parsed,
    };
    if (debouncedQ) next.q = debouncedQ;
    if (status && !presetStatus) next.status = STATUS_GROUP[status as VisibleStatus];
    if (priority) next.priority = priority;
    return next;
  }, [debouncedQ, status, priority, sort, offset, presetKey, presetStatus]);

  const tickets = useQuery({
    queryKey: ["tickets", params],
    queryFn: async () => (await api.get<Page<Ticket>>("/api/v1/tickets", { params })).data,
  });
  const admins = useQuery({
    queryKey: ["admins"],
    queryFn: async () => (await api.get<Page<User>>("/api/v1/users", { params: { limit: 100, is_active: true } })).data,
    enabled: canAssign,
  });
  const assign = useMutation({
    mutationFn: async ({ ticket, agentId }: { ticket: Ticket; agentId: string | null }) => {
      await api.post(`/api/v1/tickets/${ticket.id}/assign`, {
        agent_id: agentId,
        version: ticket.version,
      });
    },
    onSuccess: async () => {
      setAssignError(null);
      await queryClient.invalidateQueries({ queryKey: ["tickets"] });
      await queryClient.invalidateQueries({ queryKey: ["ticket-summary"] });
    },
    onError: (err) => setAssignError(getErrorMessage(err)),
  });
  const assignees = (admins.data?.items ?? []).filter((item) => item.roles?.includes("Admin"));

  return (
    <div className="space-y-4">
      <div className="card tickets-toolbar flex flex-col gap-3 p-4 lg:flex-row lg:items-center">
        <input
          className="input min-w-0 flex-1"
          placeholder="Search title or ticket number"
          value={q}
          onChange={(e) => {
            setOffset(0);
            setQ(e.target.value);
          }}
        />
        <div className="tickets-filters flex flex-wrap items-center gap-3">
          {!presetStatus && (
            <select
              className="input w-full sm:w-40"
              value={status}
              onChange={(e) => {
                setOffset(0);
                setStatus(e.target.value);
              }}
            >
              <PromptOption label="All statuses" selected={status} clearable />
              {VISIBLE_STATUSES.map((item) => (
                <option key={item} value={item}>
                  {statusLabel(item)}
                </option>
              ))}
            </select>
          )}
          <select
            className="input w-full sm:w-40"
            value={priority}
            onChange={(e) => {
              setOffset(0);
              setPriority(e.target.value as TicketPriority | "");
            }}
          >
            <PromptOption label="All priorities" selected={priority} clearable />
            <option value="CRITICAL">P1 Critical</option>
            <option value="HIGH">P2 High</option>
            <option value="MEDIUM">P3 Medium</option>
            <option value="LOW">P4 Low</option>
          </select>
          <select className="input w-full sm:w-44" value={sort} onChange={(e) => setSort(e.target.value)}>
            <option value="created_at">Newest</option>
            <option value="updated_at">Recently updated</option>
            <option value="priority">Priority</option>
            <option value="due_at">Due date</option>
          </select>
          {showCreate && (
            <Link to="/tickets/new" className="btn-primary w-full sm:w-auto">
              New ticket
            </Link>
          )}
        </div>
      </div>
      {tickets.isLoading && (
        <div className="card tickets-table-card overflow-hidden py-2" aria-hidden="true">
          {Array.from({ length: 7 }).map((_, index) => (
            <div key={index} className="skeleton-row" />
          ))}
        </div>
      )}
      {tickets.isLoading && <p className="sr-only">Loading tickets</p>}
      {tickets.isError && <p className="text-sm text-red-500">Could not load tickets. Try again.</p>}
      {assignError && <p className="text-sm text-red-500">{assignError}</p>}
      {tickets.data && (
        <TicketTable
          tickets={tickets.data.items}
          showRequester={hasPermission("ticket.view_all")}
          allowAssign={canAssign}
          allowUnassign={canUnassign}
          assignees={canAssign ? assignees : undefined}
          assigningId={assign.isPending ? assign.variables?.ticket.id : null}
          onAssign={
            canAssign || canUnassign
              ? (ticket, agentId) => assign.mutate({ ticket, agentId })
              : undefined
          }
        />
      )}
      {tickets.data && tickets.data.total > limit && (
        <div className="flex items-center justify-between text-sm">
          <p className="text-muted">
            {offset + 1}–{Math.min(offset + limit, tickets.data.total)} of {tickets.data.total}
          </p>
          <div className="space-x-2">
            <button
              className="btn-secondary disabled:opacity-40"
              disabled={offset === 0}
              onClick={() => setOffset(Math.max(0, offset - limit))}
              type="button"
            >
              Previous
            </button>
            <button
              className="btn-secondary disabled:opacity-40"
              disabled={offset + limit >= tickets.data.total}
              onClick={() => setOffset(offset + limit)}
              type="button"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
