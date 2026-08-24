import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { api, getErrorMessage } from "../../lib/api";
import type { Department, Page } from "../../lib/types";
import { useState } from "react";

const schema = z.object({
  name: z.string().min(1),
  code: z.string().min(1).max(40),
  description: z.string().optional(),
});

type FormValues = z.infer<typeof schema>;

export function DepartmentsPage() {
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);
  const departments = useQuery({
    queryKey: ["departments"],
    queryFn: async () => (await api.get<Page<Department>>("/api/v1/departments")).data,
  });
  const form = useForm<FormValues>({ resolver: zodResolver(schema) });
  const createDept = useMutation({
    mutationFn: async (values: FormValues) => api.post("/api/v1/departments", values),
    onSuccess: async () => {
      setError(null);
      form.reset();
      await queryClient.invalidateQueries({ queryKey: ["departments"] });
    },
    onError: (err) => setError(getErrorMessage(err)),
  });

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold tracking-tight">Departments</h2>
        <p className="mt-1 text-sm text-muted">Organize requesters by where they work.</p>
      </div>
      <form
        className="card flex flex-wrap gap-3 p-4"
        onSubmit={form.handleSubmit((values) => createDept.mutate(values))}
      >
        <input className="input max-w-xs" placeholder="Name" {...form.register("name")} />
        <input className="input max-w-[8rem]" placeholder="Code" {...form.register("code")} />
        <input className="input max-w-xs" placeholder="Description" {...form.register("description")} />
        <button className="btn-primary" type="submit" disabled={createDept.isPending}>
          {createDept.isPending ? "Adding…" : "Add department"}
        </button>
        {error && <p className="w-full text-sm text-red-500">{error}</p>}
      </form>
      <table className="card min-w-full overflow-hidden text-left text-sm">
        <thead className="bg-accent-soft text-muted">
          <tr>
            <th className="px-4 py-2 font-medium">Name</th>
            <th className="px-4 py-2 font-medium">Code</th>
            <th className="px-4 py-2 font-medium">Status</th>
          </tr>
        </thead>
        <tbody>
          {departments.data?.items.map((dept) => (
            <tr key={dept.id} className="border-t border-edge hover:bg-accent-soft">
              <td className="px-4 py-2">{dept.name}</td>
              <td className="px-4 py-2">{dept.code}</td>
              <td className="px-4 py-2">{dept.is_active ? "Active" : "Inactive"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
