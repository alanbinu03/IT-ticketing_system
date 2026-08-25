import { useAuth } from "../lib/auth";
import { Avatar } from "../components/ui";

export function ProfilePage() {
  const { user } = useAuth();
  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <section className="card p-6">
        <div className="flex items-center gap-4">
          <Avatar name={user?.full_name} size="lg" />
          <div>
            <h3 className="text-lg font-semibold">{user?.full_name}</h3>
            <p className="text-sm text-muted">{user?.email}</p>
            <p className="mt-1 text-xs uppercase tracking-wide text-muted">{user?.roles.join(" · ")}</p>
          </div>
        </div>
      </section>
      <dl className="card divide-y divide-edge">
        <Row label="Employee code" value={user?.employee_code ?? "—"} />
        <Row label="Username" value={user?.username ?? "—"} />
        <Row label="Department" value={user?.department?.name ?? "—"} />
        <Row label="Status" value={user?.is_active ? "Active" : "Disabled"} />
      </dl>
    </div>
  );
}

function Row({ label, value }: { label: string; value?: string }) {
  return (
    <div className="grid grid-cols-3 gap-4 px-6 py-4 text-sm">
      <dt className="text-muted">{label}</dt>
      <dd className="col-span-2 font-medium">{value}</dd>
    </div>
  );
}
