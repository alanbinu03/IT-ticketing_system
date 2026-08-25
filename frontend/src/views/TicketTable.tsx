import { Link, useNavigate } from "../lib/nav";
import type { CSSProperties } from "react";
import type { Ticket } from "../lib/tickets";
import { formatRelative } from "../lib/tickets";
import type { User } from "../lib/types";
import { PriorityBadge, PromptOption, StatusBadge } from "../components/ui";

type Props = {
  tickets: Ticket[];
  assignees?: User[];
  assigningId?: string | null;
  showRequester?: boolean;
  allowAssign?: boolean;
  allowUnassign?: boolean;
  onAssign?: (ticket: Ticket, agentId: string | null) => void;
};

export function TicketTable({
  tickets,
  assignees,
  assigningId,
  showRequester = true,
  allowAssign = true,
  allowUnassign = false,
  onAssign,
}: Props) {
  const navigate = useNavigate();
  const canAssign = Boolean(allowAssign && onAssign && assignees && assignees.length > 0);
  const canUnassign = Boolean(allowUnassign && onAssign);
  if (tickets.length === 0) {
    return (
      <div className="empty-state">
        <p className="font-semibold">No tickets match these filters</p>
        <p className="mt-1 text-sm text-muted">Try a different search, or open a new request.</p>
        <Link className="btn-primary mt-4" to="/tickets/new">
          New ticket
        </Link>
      </div>
    );
  }
  return (
    <div className="card tickets-table-card overflow-x-auto">
      <table className="data-table">
        <thead>
          <tr>
            <th>Ticket</th>
            {showRequester && <th>Requester</th>}
            <th>Priority</th>
            <th>Status</th>
            <th>Assigned to</th>
            <th>Updated</th>
          </tr>
        </thead>
        <tbody>
          {tickets.map((ticket, index) => (
            <tr
              key={ticket.id}
              className={`row-click row-enter ${
                ticket.priority === "CRITICAL"
                  ? "bg-red-500/10"
                  : !ticket.assigned_agent
                    ? "row-waiting bg-amber-500/5"
                    : ""
              } ${assigningId === ticket.id ? "row-busy" : ""}`}
              style={{ "--row": Math.min(index, 14) } as CSSProperties}
              onClick={() => navigate(`/tickets/${ticket.id}`)}
            >
              <td>
                <Link className="font-mono text-xs text-accent hover:underline" to={`/tickets/${ticket.id}`}>
                  {ticket.ticket_number}
                </Link>
                <p className="mt-0.5 font-medium">{ticket.title}</p>
                <p className="text-xs text-muted">
                  {ticket.subcategory?.name ?? ticket.category?.name ?? "Uncategorized"}
                </p>
              </td>
              {showRequester && (
                <td className="whitespace-nowrap">{ticket.requester?.full_name ?? "—"}</td>
              )}
              <td>
                <PriorityBadge priority={ticket.priority} />
              </td>
              <td>
                <StatusBadge status={ticket.status} />
              </td>
              <td
                onClick={
                  (canAssign && !ticket.assigned_agent) || (canUnassign && ticket.assigned_agent)
                    ? (event) => event.stopPropagation()
                    : undefined
                }
              >
                {canAssign && !ticket.assigned_agent ? (
                  <select
                    className="input input-sm select-assign min-w-[12rem]"
                    defaultValue=""
                    disabled={assigningId === ticket.id}
                    onChange={(e) => {
                      const agentId = e.target.value;
                      if (agentId) onAssign?.(ticket, agentId);
                      e.target.value = "";
                    }}
                  >
                    <PromptOption label="Assign to…" />
                    {assignees?.map((admin) => (
                      <option key={admin.id} value={admin.id}>
                        {admin.full_name}
                      </option>
                    ))}
                  </select>
                ) : (
                  <div className="flex items-center justify-start gap-2">
                    <span className="whitespace-nowrap font-medium">
                      {ticket.assigned_agent?.full_name ?? "Unassigned"}
                    </span>
                    {canUnassign && ticket.assigned_agent && (
                      <button
                        className="btn-table btn-table-muted"
                        type="button"
                        disabled={assigningId === ticket.id}
                        onClick={() => onAssign?.(ticket, null)}
                      >
                        {assigningId === ticket.id ? "Saving…" : "Release"}
                      </button>
                    )}
                  </div>
                )}
              </td>
              <td className="whitespace-nowrap text-muted" title={ticket.updated_at}>
                {formatRelative(ticket.updated_at)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
