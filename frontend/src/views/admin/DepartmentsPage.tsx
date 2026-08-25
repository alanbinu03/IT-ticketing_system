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
      <form
        className="card grid items-end gap-4 p-5 sm:grid-cols-[2fr_1fr_2fr_auto]"
        onSubmit={form.handleSubmit((values) => createDept.mutate(values))}
      >
        <label className="field-label">
          Name
          <input className="input" placeholder="Finance" {...form.register("name")} />
        </label>
        <label className="field-label">
          Code
          <input className="input" placeholder="FIN" {...form.register("code")} />
        </label>
        <label className="field-label">
          Description
          <input className="input" placeholder="Optional" {...form.register("description")} />
        </label>
        <button className="btn-primary w-full sm:w-auto" type="submit" disabled={createDept.isPending}>
          {createDept.isPending ? "Adding…" : "Add department"}
        </button>
        {error && <p className="text-sm text-red-500 sm:col-span-4">{error}</p>}
      </form>
      <div className="card overflow-x-auto">
        <table className="data-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Code</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {departments.data?.items.map((dept) => (
              <tr key={dept.id} className="hover:bg-accent-soft">
                <td>{dept.name}</td>
                <td>{dept.code}</td>
                <td>{dept.is_active ? "Active" : "Inactive"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
