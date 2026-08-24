import { Link, useNavigate } from "react-router-dom";
import type { Ticket } from "../lib/tickets";
import { formatRelative } from "../lib/tickets";
import type { User } from "../lib/types";
import { PriorityBadge, StatusBadge } from "../components/ui";

type Props = {
  tickets: Ticket[];
  assignees?: User[];
  currentUserId?: string;
  assigningId?: string | null;
  showRequester?: boolean;
  onAssign?: (ticket: Ticket, agentId: string) => void;
};

export function TicketTable({
  tickets,
  assignees,
  currentUserId,
  assigningId,
  showRequester = true,
  onAssign,
}: Props) {
  const navigate = useNavigate();
  const canAssign = Boolean(onAssign && assignees && assignees.length > 0);
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
    <div className="card overflow-x-auto">
      <table className="min-w-full text-left text-sm">
        <thead className="bg-accent-soft text-xs uppercase tracking-wide text-muted">
          <tr>
            <th className="px-4 py-3">Ticket</th>
            {showRequester && <th className="px-4 py-3">Requester</th>}
            <th className="px-4 py-3">Priority</th>
            <th className="px-4 py-3">Status</th>
            <th className="px-4 py-3">Owner</th>
            <th className="px-4 py-3">Updated</th>
            {canAssign && <th className="px-4 py-3">Assign</th>}
          </tr>
        </thead>
        <tbody>
          {tickets.map((ticket) => (
            <tr
              key={ticket.id}
              className={`row-click border-t border-edge ${
                ticket.priority === "CRITICAL"
                  ? "bg-red-500/10"
                  : !ticket.assigned_agent
                    ? "bg-amber-500/5"
                    : ""
              }`}
              onClick={() => navigate(`/tickets/${ticket.id}`)}
            >
              <td className="px-4 py-3">
                <Link className="font-mono text-xs text-accent hover:underline" to={`/tickets/${ticket.id}`}>
                  {ticket.ticket_number}
                </Link>
                <p className="mt-0.5 font-medium">{ticket.title}</p>
                <p className="text-xs text-muted">
                  {ticket.subcategory?.name ?? ticket.category?.name ?? "Uncategorized"}
                </p>
              </td>
              {showRequester && (
                <td className="px-4 py-3 whitespace-nowrap">{ticket.requester?.full_name ?? "—"}</td>
              )}
              <td className="px-4 py-3">
                <PriorityBadge priority={ticket.priority} />
              </td>
              <td className="px-4 py-3">
                <StatusBadge status={ticket.status} />
              </td>
              <td className="px-4 py-3 whitespace-nowrap">
                {ticket.assigned_agent?.full_name ?? "Unassigned"}
              </td>
              <td className="px-4 py-3 whitespace-nowrap text-muted" title={ticket.updated_at}>
                {formatRelative(ticket.updated_at)}
              </td>
              {canAssign && (
                <td className="px-4 py-3" onClick={(event) => event.stopPropagation()}>
                  {ticket.assigned_agent ? (
                    <span className="text-xs text-muted">—</span>
                  ) : (
                    <div className="flex min-w-[220px] items-center gap-2">
                      <select
                        className="input py-1.5 text-xs"
                        defaultValue=""
                        disabled={assigningId === ticket.id}
                        onChange={(e) => {
                          const agentId = e.target.value;
                          if (agentId) onAssign?.(ticket, agentId);
                          e.target.value = "";
                        }}
                      >
                        <option value="">Assign to…</option>
                        {assignees?.map((admin) => (
                          <option key={admin.id} value={admin.id}>
                            {admin.full_name}
                          </option>
                        ))}
                      </select>
                      {currentUserId && (
                        <button
                          className="btn-ghost whitespace-nowrap text-xs"
                          type="button"
                          disabled={assigningId === ticket.id}
                          onClick={() => onAssign?.(ticket, currentUserId)}
                        >
                          {assigningId === ticket.id ? "Saving…" : "Me"}
                        </button>
                      )}
                    </div>
                  )}
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
