import { TicketsPage } from "../TicketsPage";
import { useAuth } from "../../lib/auth";
import { ACTIVE_QUEUE_STATUSES, COMPLETED_QUEUE_STATUSES } from "../../lib/tickets";

export function MyQueuePage() {
  const { user } = useAuth();
  if (!user) return null;
  return (
    <TicketsPage
      title="Assigned to me"
      showCreate={false}
      enableAssign={false}
      enableUnassign
      description="Open work assigned to you. Only you see this queue."
      preset={{ assigned_agent_id: user.id, status: ACTIVE_QUEUE_STATUSES }}
    />
  );
}

export function UnassignedQueuePage() {
  return (
    <TicketsPage
      title="Unassigned"
      showCreate={false}
      enableUnassign={false}
      description="Requests waiting for an admin. Every admin sees the same list."
      preset={{ unassigned: true }}
    />
  );
}

export function CompletedQueuePage() {
  return (
    <TicketsPage
      title="Completed"
      showCreate={false}
      enableAssign={false}
      enableUnassign={false}
      description="Completed and closed tickets. Every admin sees the same list."
      preset={{ status: COMPLETED_QUEUE_STATUSES }}
    />
  );
}
