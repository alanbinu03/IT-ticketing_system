import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { useNavigate } from "../lib/nav";
import { api } from "../lib/api";

type NotificationItem = {
  id: string;
  type: string;
  title: string;
  body: string;
  link: string | null;
  ticket_id: string | null;
  read_at: string | null;
  created_at: string;
};

type NotificationList = {
  items: NotificationItem[];
  total: number;
  unread_count: number;
};

export function NotificationBell() {
  const navigate = useNavigate();
  const rootRef = useRef<HTMLDivElement>(null);
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState<NotificationItem[]>([]);
  const [unread, setUnread] = useState(0);
  const [toast, setToast] = useState<NotificationItem | null>(null);
  const seen = useRef<Set<string>>(new Set());
  const primed = useRef(false);

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      try {
        const { data } = await api.get<NotificationList>("/api/v1/notifications", {
          params: { limit: 12 },
        });
        if (cancelled) return;
        const unreadItems = data.items.filter((item) => !item.read_at);
        if (primed.current) {
          const fresh = unreadItems.find((item) => !seen.current.has(item.id));
          if (fresh) setToast(fresh);
        }
        unreadItems.forEach((item) => seen.current.add(item.id));
        primed.current = true;
        setItems(data.items);
        setUnread(data.unread_count);
      } catch {
        /* ignore polling errors */
      }
    };

    void load();
    const timer = window.setInterval(() => void load(), 8000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, []);

  useEffect(() => {
    if (!toast) return;
    const timer = window.setTimeout(() => setToast(null), 8000);
    return () => window.clearTimeout(timer);
  }, [toast]);

  useEffect(() => {
    if (!open) return;
    const onPointer = (event: MouseEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onPointer);
    return () => document.removeEventListener("mousedown", onPointer);
  }, [open]);

  const openItem = async (item: NotificationItem) => {
    setToast(null);
    setOpen(false);
    try {
      await api.post(`/api/v1/notifications/${item.id}/read`);
      setItems((current) =>
        current.map((row) => (row.id === item.id ? { ...row, read_at: new Date().toISOString() } : row)),
      );
      setUnread((count) => Math.max(0, count - (item.read_at ? 0 : 1)));
    } catch {
      /* still navigate */
    }
    if (item.link) navigate(item.link);
  };

  return (
    <div className="relative" ref={rootRef}>
      <button
        type="button"
        className="icon-btn relative"
        aria-label={unread > 0 ? `${unread} unread notifications` : "Notifications"}
        title="Notifications"
        onClick={() => setOpen((value) => !value)}
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true">
          <path
            d="M6.4 9.6a5.6 5.6 0 1 1 11.2 0c0 3.2 1.1 4.6 1.8 5.4.3.3.1.9-.4.9H5a.6.6 0 0 1-.4-.9c.7-.8 1.8-2.2 1.8-5.4Z"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinejoin="round"
          />
          <path d="M10 18.5a2 2 0 0 0 4 0" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
        </svg>
        {unread > 0 && (
          <span className="absolute -right-1 -top-1 min-w-4 rounded-full bg-red-500 px-1 text-[10px] font-semibold text-white">
            {unread > 9 ? "9+" : unread}
          </span>
        )}
      </button>
      {open && (
        <div className="absolute right-0 z-30 mt-2 w-80 overflow-hidden rounded-2xl border border-edge bg-surface shadow-xl">
          <div className="flex h-12 items-center justify-between border-b border-edge px-4">
            <p className="text-sm font-medium">Notifications</p>
            {unread > 0 && (
              <button
                type="button"
                className="btn-ghost text-xs"
                onClick={async () => {
                  await api.post("/api/v1/notifications/read-all");
                  setItems((current) =>
                    current.map((item) => ({ ...item, read_at: item.read_at ?? new Date().toISOString() })),
                  );
                  setUnread(0);
                }}
              >
                Mark all read
              </button>
            )}
          </div>
          <ul className="max-h-80 overflow-y-auto">
            {items.length === 0 && <li className="px-4 py-4 text-sm text-muted">No notifications yet.</li>}
            {items.map((item) => (
              <li key={item.id}>
                <button
                  type="button"
                  className={`w-full bg-transparent px-4 py-3 text-left text-sm hover:bg-accent-soft ${item.read_at ? "opacity-70" : ""}`}
                  onClick={() => void openItem(item)}
                >
                  <p className="font-medium">{item.title}</p>
                  <p className="text-xs text-muted">{item.body}</p>
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
      {toast &&
        createPortal(
          <button type="button" className="notice-toast" onClick={() => void openItem(toast)}>
            <p className="text-xs uppercase tracking-wide text-white/80">New ticket</p>
            <p className="mt-1 font-semibold">{toast.title}</p>
            <p className="mt-1 text-sm text-white/90">{toast.body}</p>
          </button>,
          document.body,
        )}
    </div>
  );
}
