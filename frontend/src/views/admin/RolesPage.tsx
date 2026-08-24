import { useQuery } from "@tanstack/react-query";
import { api } from "../../lib/api";
import type { Role } from "../../lib/types";

export function RolesPage() {
  const roles = useQuery({
    queryKey: ["roles"],
    queryFn: async () => (await api.get<Role[]>("/api/v1/roles")).data,
  });

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-2xl font-semibold tracking-tight">Roles</h2>
        <p className="mt-1 text-sm text-muted">What each account is allowed to do.</p>
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        {roles.data?.map((role) => (
          <section key={role.id} className="card p-4">
            <div className="flex items-center justify-between">
              <h3 className="font-medium">{role.name}</h3>
              {role.is_system && (
                <span className="rounded bg-accent-soft px-2 py-0.5 text-xs text-muted">System</span>
              )}
            </div>
            <p className="mt-1 text-sm text-muted">{role.description}</p>
            <ul className="mt-3 flex flex-wrap gap-1">
              {role.permissions.map((permission) => (
                <li key={permission.id} className="rounded bg-accent-soft px-2 py-0.5 text-xs">
                  {permission.code}
                </li>
              ))}
            </ul>
          </section>
        ))}
      </div>
    </div>
  );
}
