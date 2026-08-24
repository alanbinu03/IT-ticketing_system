import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { api, getErrorMessage } from "../../lib/api";
import type { Department, Page, Team, User } from "../../lib/types";
import { useState } from "react";

const schema = z.object({
  name: z.string().min(1),
  code: z.string().min(1),
  department_id: z.string().min(1),
});

type FormValues = z.infer<typeof schema>;

export function TeamsPage() {
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const teams = useQuery({
    queryKey: ["teams"],
    queryFn: async () => (await api.get<Page<Team>>("/api/v1/teams")).data,
  });
  const departments = useQuery({
    queryKey: ["departments"],
    queryFn: async () => (await api.get<Page<Department>>("/api/v1/departments")).data,
  });
  const users = useQuery({
    queryKey: ["users"],
    queryFn: async () => (await api.get<Page<User>>("/api/v1/users?limit=100")).data,
  });
  const detail = useQuery({
    queryKey: ["team", selected],
    enabled: Boolean(selected),
    queryFn: async () => (await api.get<Team>(`/api/v1/teams/${selected}`)).data,
  });
  const form = useForm<FormValues>({ resolver: zodResolver(schema) });
  const createTeam = useMutation({
    mutationFn: async (values: FormValues) => api.post("/api/v1/teams", values),
    onSuccess: async () => {
      setError(null);
      form.reset();
      await queryClient.invalidateQueries({ queryKey: ["teams"] });
    },
    onError: (err) => setError(getErrorMessage(err)),
  });
  const addMember = useMutation({
    mutationFn: async (userId: string) =>
      api.post(`/api/v1/teams/${selected}/members`, { user_id: userId, is_lead: false }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["team", selected] });
    },
  });

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold tracking-tight">IT Teams</h2>
        <p className="mt-1 text-sm text-muted">Group admins who share a queue.</p>
      </div>
      <form
        className="card flex flex-wrap gap-3 p-4"
        onSubmit={form.handleSubmit((values) => createTeam.mutate(values))}
      >
        <input className="input max-w-xs" placeholder="Name" {...form.register("name")} />
        <input className="input max-w-[8rem]" placeholder="Code" {...form.register("code")} />
        <select className="input max-w-xs" {...form.register("department_id")}>
          <option value="">Department</option>
          {departments.data?.items.map((dept) => (
            <option key={dept.id} value={dept.id}>
              {dept.name}
            </option>
          ))}
        </select>
        <button className="btn-primary" type="submit">
          Add team
        </button>
        {error && <p className="w-full text-sm text-red-500">{error}</p>}
      </form>
      <div className="grid gap-4 lg:grid-cols-2">
        <table className="card min-w-full overflow-hidden text-left text-sm">
          <thead className="bg-accent-soft text-muted">
            <tr>
              <th className="px-4 py-2 font-medium">Team</th>
              <th className="px-4 py-2 font-medium">Code</th>
              <th className="px-4 py-2 font-medium">Department</th>
            </tr>
          </thead>
          <tbody>
            {teams.data?.items.map((team) => (
              <tr
                key={team.id}
                className={`row-click border-t border-edge ${selected === team.id ? "bg-accent-soft" : ""}`}
                onClick={() => setSelected(team.id)}
              >
                <td className="px-4 py-2">{team.name}</td>
                <td className="px-4 py-2">{team.code}</td>
                <td className="px-4 py-2">{team.department?.name ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <section className="card p-4">
          <h3 className="font-medium">Members</h3>
          {!selected && <p className="mt-2 text-sm text-muted">Select a team.</p>}
          {detail.data && (
            <>
              <ul className="mt-3 space-y-1 text-sm">
                {detail.data.members?.length ? (
                  detail.data.members.map((member) => (
                    <li key={member.user_id}>
                      {member.full_name}{" "}
                      <span className="text-muted">({member.email})</span>
                      {member.is_lead ? " · Lead" : ""}
                    </li>
                  ))
                ) : (
                  <li className="text-muted">No members yet.</li>
                )}
              </ul>
              <select
                className="input mt-4"
                defaultValue=""
                onChange={(event) => {
                  if (event.target.value) {
                    addMember.mutate(event.target.value);
                    event.target.value = "";
                  }
                }}
              >
                <option value="">Add member…</option>
                {users.data?.items.map((user) => (
                  <option key={user.id} value={user.id}>
                    {user.full_name}
                  </option>
                ))}
              </select>
            </>
          )}
        </section>
      </div>
    </div>
  );
}
