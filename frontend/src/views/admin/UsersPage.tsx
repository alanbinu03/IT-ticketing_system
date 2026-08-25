import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { api, getErrorMessage } from "../../lib/api";
import { useAuth } from "../../lib/auth";
import { accountEmailSchema } from "../../lib/email";
import type { Department, Page, Role, User } from "../../lib/types";
import { PromptOption } from "../../components/ui";
import { useEffect, useRef, useState } from "react";

const schema = z.object({
  email: accountEmailSchema,
  password: z.string().min(8, "Password must be at least 8 characters"),
  full_name: z.string().trim().min(1, "Name is required"),
  department_id: z.string().optional(),
  role_id: z.string().optional(),
});

type FormValues = z.infer<typeof schema>;

type ImportResult = {
  created: number;
  skipped: number;
  errors: { row: number; email: string | null; message: string }[];
};

const TEMPLATE_CSV = "name,email,password\nJane Employee,jane@hirect.com,Welcome123\n";

export function UsersPage() {
  const queryClient = useQueryClient();
  const { user: currentUser, hasPermission } = useAuth();
  const fileInput = useRef<HTMLInputElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [importResult, setImportResult] = useState<ImportResult | null>(null);
  const [pendingDelete, setPendingDelete] = useState<User | null>(null);
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
  const fieldErrors = form.formState.errors;
  const employeeRoleId = roles.data?.find((role) => role.name.toLowerCase() === "employee")?.id ?? "";

  useEffect(() => {
    if (employeeRoleId && !form.getValues("role_id")) {
      form.setValue("role_id", employeeRoleId);
    }
  }, [employeeRoleId, form]);

  const createUser = useMutation({
    mutationFn: async (values: FormValues) => {
      await api.post("/api/v1/users", {
        email: values.email,
        password: values.password,
        full_name: values.full_name,
        department_id: values.department_id || null,
        role_ids: values.role_id ? [values.role_id] : [],
      });
    },
    onSuccess: async () => {
      setError(null);
      form.reset({ role_id: employeeRoleId });
      await queryClient.invalidateQueries({ queryKey: ["users"] });
    },
    onError: (err) => setError(getErrorMessage(err)),
  });

  const importUsers = useMutation({
    mutationFn: async (file: File) => {
      const body = new FormData();
      body.append("file", file);
      return (await api.post<ImportResult>("/api/v1/users/import", body)).data;
    },
    onSuccess: async (result) => {
      setError(null);
      setImportResult(result);
      await queryClient.invalidateQueries({ queryKey: ["users"] });
    },
    onError: (err) => setError(getErrorMessage(err, "Could not import the user list.")),
  });

  const disableUser = useMutation({
    mutationFn: async (id: string) => api.post(`/api/v1/users/${id}/disable`),
    onSuccess: async () => queryClient.invalidateQueries({ queryKey: ["users"] }),
  });

  const enableUser = useMutation({
    mutationFn: async (id: string) => api.patch(`/api/v1/users/${id}`, { is_active: true }),
    onSuccess: async () => queryClient.invalidateQueries({ queryKey: ["users"] }),
  });

  const deleteUser = useMutation({
    mutationFn: async (id: string) => api.delete(`/api/v1/users/${id}`),
    onSuccess: async () => {
      setError(null);
      setPendingDelete(null);
      await queryClient.invalidateQueries({ queryKey: ["users"] });
    },
    onError: (err) => setError(getErrorMessage(err, "Could not delete this user.")),
  });

  const canDeleteUsers = hasPermission("user.delete") || hasPermission("user.disable");

  const downloadTemplate = () => {
    const blob = new Blob([TEMPLATE_CSV], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "hirect-users-template.csv";
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6">
      <div className="card flex flex-wrap items-center justify-between gap-3 p-5">
        <p className="min-w-0 flex-1 text-sm leading-6 text-muted">
          Upload an Excel or CSV sheet with columns <span className="font-medium text-ink">name</span>,{" "}
          <span className="font-medium text-ink">email</span>, and{" "}
          <span className="font-medium text-ink">password</span>.
        </p>
        <div className="flex flex-wrap gap-2">
          <button className="btn-secondary" type="button" onClick={downloadTemplate}>
            Download template
          </button>
          <input
            ref={fileInput}
            className="hidden"
            type="file"
            accept=".xlsx,.csv,text/csv,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (file) importUsers.mutate(file);
              event.target.value = "";
            }}
          />
          <button
            className="btn-primary"
            type="button"
            disabled={importUsers.isPending}
            onClick={() => fileInput.current?.click()}
          >
            {importUsers.isPending ? "Importing…" : "Import Excel / CSV"}
          </button>
        </div>
        {importResult && (
          <p className="w-full text-sm text-muted">
            Created {importResult.created} account{importResult.created === 1 ? "" : "s"}. Skipped {importResult.skipped}.
          </p>
        )}
        {importResult?.errors.length ? (
          <ul className="w-full text-sm text-red-500">
            {importResult.errors.slice(0, 8).map((item) => (
              <li key={`${item.row}-${item.email}`}>
                Row {item.row}
                {item.email ? ` (${item.email})` : ""}: {item.message}
              </li>
            ))}
          </ul>
        ) : null}
      </div>
      <form
        className="card grid gap-4 p-5 sm:grid-cols-2 xl:grid-cols-3"
        noValidate
        onSubmit={form.handleSubmit((values) => createUser.mutate(values))}
      >
        <label className="field-label">
          Full name
          <input className="input" placeholder="Jane Employee" {...form.register("full_name")} />
          {fieldErrors.full_name && (
            <p className="text-xs font-normal text-red-500">{fieldErrors.full_name.message}</p>
          )}
        </label>
        <label className="field-label">
          Email
          <input
            className="input"
            type="text"
            inputMode="email"
            autoCapitalize="none"
            autoCorrect="off"
            spellCheck={false}
            placeholder="jane@hirect.com"
            {...form.register("email")}
          />
          {fieldErrors.email && <p className="text-xs font-normal text-red-500">{fieldErrors.email.message}</p>}
        </label>
        <label className="field-label">
          Password
          <input className="input" placeholder="At least 8 characters" type="password" {...form.register("password")} />
          {fieldErrors.password && (
            <p className="text-xs font-normal text-red-500">{fieldErrors.password.message}</p>
          )}
        </label>
        <label className="field-label">
          Department
          <select className="input" {...form.register("department_id")}>
            <PromptOption label="No department" selected={form.watch("department_id") ?? ""} clearable />
            {departments.data?.items.map((dept) => (
              <option key={dept.id} value={dept.id}>
                {dept.name}
              </option>
            ))}
          </select>
        </label>
        <label className="field-label">
          Role
          <select className="input" {...form.register("role_id")}>
            {roles.data?.map((role) => (
              <option key={role.id} value={role.id}>
                {role.name}
              </option>
            ))}
          </select>
        </label>
        <div className="flex items-end">
          <button className="btn-primary w-full" type="submit" disabled={createUser.isPending}>
            {createUser.isPending ? "Creating…" : "Create user"}
          </button>
        </div>
        {error && <p className="text-sm text-red-500 sm:col-span-2 xl:col-span-3">{error}</p>}
      </form>
      <div className="card overflow-x-auto">
        <table className="data-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Email</th>
              <th>Department</th>
              <th>Roles</th>
              <th>Status</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {users.data?.items.map((user) => (
              <tr key={user.id} className="hover:bg-accent-soft">
                <td>{user.full_name}</td>
                <td>{user.email}</td>
                <td>{user.department?.name ?? "—"}</td>
                <td>{user.roles.join(", ")}</td>
                <td>{user.is_active ? "Active" : "Disabled"}</td>
                <td className="text-right">
                  <div className="flex justify-end gap-2">
                    {user.is_active ? (
                      <button
                        className="btn-table btn-table-danger"
                        type="button"
                        disabled={disableUser.isPending}
                        onClick={() => disableUser.mutate(user.id)}
                      >
                        {disableUser.isPending && disableUser.variables === user.id ? "Saving…" : "Disable"}
                      </button>
                    ) : (
                      <button
                        className="btn-table btn-table-success"
                        type="button"
                        disabled={enableUser.isPending}
                        onClick={() => enableUser.mutate(user.id)}
                      >
                        {enableUser.isPending && enableUser.variables === user.id ? "Saving…" : "Enable"}
                      </button>
                    )}
                    {canDeleteUsers && user.id !== currentUser?.id && (
                      <button
                        className="btn-table btn-table-danger"
                        type="button"
                        onClick={() => {
                          setError(null);
                          setPendingDelete(user);
                        }}
                      >
                        Delete
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {pendingDelete && (
        <div className="modal-scrim" role="presentation" onClick={() => setPendingDelete(null)}>
          <div
            className="modal-card card p-5"
            role="dialog"
            aria-modal="true"
            aria-labelledby="delete-user-title"
            onClick={(event) => event.stopPropagation()}
          >
            <h3 id="delete-user-title" className="text-lg font-semibold tracking-tight">
              Delete this user?
            </h3>
            <p className="mt-2 text-sm text-muted">
              Are you sure you want to delete {pendingDelete.full_name} ({pendingDelete.email})? This cannot be
              undone.
            </p>
            {error && <p className="mt-3 text-sm text-red-500">{error}</p>}
            <div className="mt-5 flex justify-end gap-2">
              <button className="btn-secondary" type="button" onClick={() => setPendingDelete(null)}>
                Cancel
              </button>
              <button
                className="btn-danger"
                type="button"
                disabled={deleteUser.isPending}
                onClick={() => deleteUser.mutate(pendingDelete.id)}
              >
                {deleteUser.isPending ? "Deleting…" : "Yes, delete user"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
