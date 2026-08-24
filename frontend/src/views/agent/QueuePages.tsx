import { TicketsPage } from "../TicketsPage";
import { useAuth } from "../../lib/auth";

export function MyQueuePage() {
  const { user } = useAuth();
  if (!user) return null;
  return <TicketsPage title="Assigned to me" showCreate={false} preset={{ assigned_agent_id: user.id }} />;
}

export function UnassignedQueuePage() {
  return <TicketsPage title="Unassigned" showCreate={false} preset={{ unassigned: true }} />;
}
