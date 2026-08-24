import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { api, getErrorMessage } from "../../lib/api";
import type { Department, Page, Role, User } from "../../lib/types";
import { useState } from "react";

const schema = z.object({
  email: z.string().email(),
  password: z.string().min(8),
  full_name: z.string().min(1),
  department_id: z.string().optional(),
  role_id: z.string().min(1, "Select a role"),
});

type FormValues = z.infer<typeof schema>;

export function UsersPage() {
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);
  const users = useQuery({
    queryKey: ["users"],
    queryFn: async () => (await api.get<Page<User>>("/api/v1/users")).data,
  });
  const departments = useQuery({
    queryKey: ["departments"],
    queryFn: async () => (await api.get<Page<Department>>("/api/v1/departments")).data,
  });
  const roles = useQuery({
    queryKey: ["roles"],
    queryFn: async () => (await api.get<Role[]>("/api/v1/roles")).data,
  });
  const form = useForm<FormValues>({ resolver: zodResolver(schema) });

  const createUser = useMutation({
    mutationFn: async (values: FormValues) => {
      await api.post("/api/v1/users", {
        email: values.email,
        password: values.password,
        full_name: values.full_name,
        department_id: values.department_id || null,
        role_ids: [values.role_id],
      });
    },
    onSuccess: async () => {
      setError(null);
      form.reset();
      await queryClient.invalidateQueries({ queryKey: ["users"] });
    },
    onError: (err) => setError(getErrorMessage(err)),
  });

  const disableUser = useMutation({
    mutationFn: async (id: string) => api.post(`/api/v1/users/${id}/disable`),
    onSuccess: async () => queryClient.invalidateQueries({ queryKey: ["users"] }),
  });

  const enableUser = useMutation({
    mutationFn: async (id: string) => api.patch(`/api/v1/users/${id}`, { is_active: true }),
    onSuccess: async () => queryClient.invalidateQueries({ queryKey: ["users"] }),
  });

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold tracking-tight">Users</h2>
        <p className="mt-1 text-sm text-muted">Create accounts and keep access current.</p>
      </div>
      <form
        className="card grid gap-3 p-4 md:grid-cols-2 lg:grid-cols-5"
        onSubmit={form.handleSubmit((values) => createUser.mutate(values))}
      >
        <input className="input" placeholder="Full name" {...form.register("full_name")} />
        <input className="input" placeholder="Email" {...form.register("email")} />
        <input className="input" placeholder="Password" type="password" {...form.register("password")} />
        <select className="input" {...form.register("department_id")}>
          <option value="">No department</option>
          {departments.data?.items.map((dept) => (
            <option key={dept.id} value={dept.id}>
              {dept.name}
            </option>
          ))}
        </select>
        <select className="input" {...form.register("role_id")}>
          <option value="">Select role</option>
          {roles.data?.map((role) => (
            <option key={role.id} value={role.id}>
              {role.name}
            </option>
          ))}
        </select>
        <button className="btn-primary md:col-span-2 lg:col-span-1" type="submit" disabled={createUser.isPending}>
          {createUser.isPending ? "Creating…" : "Create user"}
        </button>
        {error && <p className="text-sm text-red-500 md:col-span-2 lg:col-span-5">{error}</p>}
      </form>
      <div className="card overflow-x-auto">
        <table className="min-w-full text-left text-sm">
          <thead className="bg-accent-soft text-muted">
            <tr>
              <th className="px-4 py-2 font-medium">Name</th>
              <th className="px-4 py-2 font-medium">Email</th>
              <th className="px-4 py-2 font-medium">Department</th>
              <th className="px-4 py-2 font-medium">Roles</th>
              <th className="px-4 py-2 font-medium">Status</th>
              <th className="px-4 py-2 font-medium" />
            </tr>
          </thead>
          <tbody>
            {users.data?.items.map((user) => (
              <tr key={user.id} className="border-t border-edge hover:bg-accent-soft">
                <td className="px-4 py-2">{user.full_name}</td>
                <td className="px-4 py-2">{user.email}</td>
                <td className="px-4 py-2">{user.department?.name ?? "—"}</td>
                <td className="px-4 py-2">{user.roles.join(", ")}</td>
                <td className="px-4 py-2">{user.is_active ? "Active" : "Disabled"}</td>
                <td className="px-4 py-2 text-right">
                  {user.is_active ? (
                    <button
                      className="text-red-700 hover:underline"
                      type="button"
                      onClick={() => disableUser.mutate(user.id)}
                    >
                      Disable
                    </button>
                  ) : (
                    <button
                      className="text-emerald-700 hover:underline"
                      type="button"
                      onClick={() => enableUser.mutate(user.id)}
                    >
                      Enable
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
