import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { Link, useNavigate } from "react-router-dom";
import { api, getErrorMessage } from "../lib/api";
import type { Category, TicketPriority } from "../lib/tickets";
import { useState } from "react";
import { BackLink, PageHeader } from "../components/ui";

const schema = z.object({
  title: z.string().min(3, "Give this a short, clear title"),
  description: z.string().min(8, "Add enough detail for IT to start"),
  category_id: z.string().optional(),
  subcategory_id: z.string().optional(),
  priority: z.enum(["CRITICAL", "HIGH", "MEDIUM", "LOW"]),
  severity: z.enum(["CRITICAL", "HIGH", "MEDIUM", "LOW"]),
});

type FormValues = z.infer<typeof schema>;

const PRIORITIES: { value: TicketPriority; label: string; hint: string }[] = [
  { value: "CRITICAL", label: "P1 Critical", hint: "Work is blocked for many people" },
  { value: "HIGH", label: "P2 High", hint: "Important, needs attention today" },
  { value: "MEDIUM", label: "P3 Medium", hint: "Normal request, can wait a bit" },
  { value: "LOW", label: "P4 Low", hint: "Nice to have or minor issue" },
];

export function NewTicketPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);
  const [created, setCreated] = useState<{ id: string; ticket_number: string } | null>(null);
  const categories = useQuery({
    queryKey: ["categories"],
    queryFn: async () => (await api.get<Category[]>("/api/v1/categories")).data,
  });
  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { priority: "MEDIUM", severity: "MEDIUM" },
  });
  const categoryId = form.watch("category_id");
  const priority = form.watch("priority");
  const selected = categories.data?.find((item) => item.id === categoryId);

  const createTicket = useMutation({
    mutationFn: async (values: FormValues) => {
      const { data } = await api.post("/api/v1/tickets", {
        ...values,
        category_id: values.category_id || null,
        subcategory_id: values.subcategory_id || null,
      });
      return data;
    },
    onSuccess: async (ticket: { id: string; ticket_number: string }) => {
      await queryClient.invalidateQueries({ queryKey: ["tickets"] });
      await queryClient.invalidateQueries({ queryKey: ["ticket-summary"] });
      setCreated(ticket);
    },
    onError: (err) => setError(getErrorMessage(err)),
  });

  if (created) {
    return (
      <div className="mx-auto max-w-xl space-y-4">
        <div className="empty-state">
          <p className="text-lg font-semibold">Ticket submitted successfully</p>
          <p className="mt-2 font-mono text-sm">{created.ticket_number}</p>
          <p className="mt-2 text-sm text-muted">Our IT team has been notified.</p>
          <div className="mt-5 flex justify-center gap-3">
            <Link className="btn-primary" to={`/tickets/${created.id}`}>
              Open ticket
            </Link>
            <Link className="btn-secondary" to="/tickets">
              Back to tickets
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl space-y-5">
      <div>
        <BackLink to="/tickets">← Back to tickets</BackLink>
        <div className="mt-3">
          <PageHeader
            title="New ticket"
            description="Tell IT what broke, who is affected, and how urgent it is."
          />
        </div>
      </div>
      <form
        className="card space-y-5 p-6"
        onSubmit={form.handleSubmit((values) => createTicket.mutate(values))}
      >
        <label className="block text-sm font-medium">
          Title
          <input className="input mt-1" placeholder="Cannot connect to VPN" {...form.register("title")} />
          {form.formState.errors.title && (
            <p className="mt-1 text-xs text-red-500">{form.formState.errors.title.message}</p>
          )}
        </label>
        <label className="block text-sm font-medium">
          What happened?
          <textarea
            className="input mt-1"
            rows={6}
            placeholder="What you were doing, what you expected, and any error messages."
            {...form.register("description")}
          />
          {form.formState.errors.description && (
            <p className="mt-1 text-xs text-red-500">{form.formState.errors.description.message}</p>
          )}
        </label>
        <div>
          <p className="text-sm font-medium">How urgent is this?</p>
          <div className="mt-2 grid gap-2 sm:grid-cols-2">
            {PRIORITIES.map((item) => (
              <button
                key={item.value}
                type="button"
                className={`choice-card ${priority === item.value ? "is-selected" : ""}`}
                onClick={() => {
                  form.setValue("priority", item.value);
                  form.setValue("severity", item.value);
                }}
              >
                <p className="text-sm font-semibold">{item.label}</p>
                <p className="mt-0.5 text-xs text-muted">{item.hint}</p>
              </button>
            ))}
          </div>
        </div>
        <div className="grid gap-3 md:grid-cols-2">
          <label className="block text-sm font-medium">
            Category
            <select
              className="input mt-1"
              {...form.register("category_id", {
                onChange: () => form.setValue("subcategory_id", ""),
              })}
            >
              <option value="">Optional</option>
              {categories.data?.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name}
                </option>
              ))}
            </select>
          </label>
          <label className="block text-sm font-medium">
            Subcategory
            <select className="input mt-1" {...form.register("subcategory_id")}>
              <option value="">Optional</option>
              {selected?.children.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name}
                </option>
              ))}
            </select>
          </label>
        </div>
        <label className="block text-sm font-medium">
          Attachments
          <input className="input mt-1" type="file" disabled />
          <p className="mt-1 text-xs text-muted">File uploads will be available in a later release.</p>
        </label>
        {error && <p className="text-sm text-red-500">{error}</p>}
        <div className="flex items-center gap-3">
          <button className="btn-primary" disabled={createTicket.isPending} type="submit">
            {createTicket.isPending ? "Submitting…" : "Submit ticket"}
          </button>
          <button className="btn-secondary" type="button" onClick={() => navigate("/tickets")}>
            Cancel
          </button>
        </div>
      </form>
    </div>
  );
}
