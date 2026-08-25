import { useEffect, useState } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { Link, NavLink } from "../lib/nav";
import { canViewTransition } from "../lib/motion";
import { useAuth } from "../lib/auth";
import { BrandLogo } from "./BrandLogo";
import { Avatar } from "./ui";
import { ThemeSwitcher } from "./ThemeSwitcher";
import { NotificationBell } from "./NotificationBell";

const linkClass = ({ isActive }: { isActive: boolean }) =>
  `nav-link flex h-10 items-center rounded-xl px-4 text-sm font-medium ${
    isActive ? "is-active bg-sidebar-active text-white shadow-sm" : "text-sidebar-muted hover:bg-sidebar-hover hover:text-white"
  }`;

const TITLES: Record<string, string> = {
  "/dashboard": "Dashboard",
  "/admin/dashboard": "Admin dashboard",
  "/admin/login": "Admin sign in",
  "/tickets": "Tickets",
  "/tickets/new": "New ticket",
  "/profile": "Profile",
  "/agent/my-queue": "Assigned to me",
  "/agent/unassigned": "Unassigned",
  "/agent/completed": "Completed",
  "/admin/users": "Users",
  "/admin/departments": "Departments",
};

const SUBTITLES: Record<string, string> = {
  "/tickets": "Every request in one list",
  "/tickets/new": "Tell IT what broke and how urgent it is",
  "/profile": "How this workspace sees you",
  "/agent/my-queue": "Open work assigned to you",
  "/agent/unassigned": "Waiting for an admin — every admin sees this",
  "/agent/completed": "Finished work — every admin sees this",
  "/admin/users": "Create accounts and manage access",
  "/admin/departments": "Organize people by where they work",
};

function pageTitle(pathname: string): string {
  if (TITLES[pathname]) return TITLES[pathname];
  if (pathname.startsWith("/tickets/")) return "Ticket";
  return "Workspace";
}

function pageSubtitle(pathname: string): string | null {
  if (SUBTITLES[pathname]) return SUBTITLES[pathname];
  if (pathname.startsWith("/tickets/")) return "Thread, assignment, and status";
  return null;
}

function PageStage() {
  const location = useLocation();
  const [cssEnter, setCssEnter] = useState(true);

  useEffect(() => {
    setCssEnter(!canViewTransition());
  }, []);

  return (
    <div key={cssEnter ? location.pathname : "stage"} className={cssEnter ? "page-stage page-enter" : "page-stage"}>
      <Outlet />
    </div>
  );
}

export function AppLayout() {
  const location = useLocation();
  const { user, logout, hasPermission } = useAuth();
  const [navOpen, setNavOpen] = useState(false);
  const showAdmin = hasPermission("user.view") || hasPermission("department.manage");
  const subtitle = pageSubtitle(location.pathname);

  useEffect(() => {
    setNavOpen(false);
  }, [location.pathname]);

  return (
    <div className="app-shell lg:grid lg:grid-cols-[var(--sidebar-w)_minmax(0,1fr)]">
      {navOpen && <button type="button" className="app-scrim" aria-label="Close menu" onClick={() => setNavOpen(false)} />}
      <aside className={`app-sidebar flex flex-col px-4 py-4 ${navOpen ? "is-open" : ""}`}>
        <NavLink to="/dashboard" className="nav-brand">
          <BrandLogo size="sidebar" />
          <h1 className="mt-2 text-sm font-semibold tracking-tight">IT Ticketing</h1>
        </NavLink>
        <nav className="mt-6 flex min-h-0 flex-1 flex-col overflow-y-auto">
          <div className="space-y-1">
            <NavLink to="/dashboard" className={linkClass}>
              Dashboard
            </NavLink>
            <NavLink to="/tickets" className={linkClass}>
              Tickets
            </NavLink>
            {hasPermission("ticket.view_all") && (
              <>
                <p className="px-4 pb-2 pt-6 text-[11px] font-semibold uppercase tracking-[0.16em] text-sidebar-muted">
                  Queues
                </p>
                <NavLink to="/agent/my-queue" className={linkClass}>
                  Assigned to me
                </NavLink>
                <NavLink to="/agent/unassigned" className={linkClass}>
                  Unassigned
                </NavLink>
                <NavLink to="/agent/completed" className={linkClass}>
                  Completed
                </NavLink>
              </>
            )}
            {showAdmin && (
              <>
                <p className="px-4 pb-2 pt-6 text-[11px] font-semibold uppercase tracking-[0.16em] text-sidebar-muted">
                  Administration
                </p>
                {hasPermission("user.view") && (
                  <NavLink to="/admin/users" className={linkClass}>
                    Users
                  </NavLink>
                )}
                {hasPermission("department.manage") && (
                  <NavLink to="/admin/departments" className={linkClass}>
                    Departments
                  </NavLink>
                )}
              </>
            )}
          </div>
          <div className="mt-auto border-t border-white/10 pt-3">
            <NavLink to="/profile" className={linkClass}>
              Profile
            </NavLink>
          </div>
        </nav>
      </aside>
      <div className="app-content">
        <header className="app-header justify-between gap-4 border-b border-edge px-4 lg:px-6">
          <div className="flex min-w-0 items-center gap-3">
            <button type="button" className="icon-btn lg:hidden" aria-label="Open menu" onClick={() => setNavOpen(true)}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <path d="M4 7h16M4 12h16M4 17h16" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
              </svg>
            </button>
            <div className="min-w-0">
              <p className="truncate text-base font-semibold leading-5">{pageTitle(location.pathname)}</p>
              {subtitle && <p className="hidden truncate text-xs leading-4 text-muted sm:block">{subtitle}</p>}
            </div>
          </div>
          <div className="flex h-10 shrink-0 items-center gap-2">
            {hasPermission("ticket.view_all") && <NotificationBell />}
            <ThemeSwitcher />
            <Link to="/profile" className="hidden h-10 items-center gap-2 rounded-xl px-2 transition-colors hover:bg-accent-soft sm:flex">
              <Avatar name={user?.full_name} size="sm" />
              <span className="hidden text-left xl:block">
                <p className="text-sm font-medium leading-4">{user?.full_name}</p>
                <p className="text-xs leading-4 text-muted">{user?.roles.join(", ")}</p>
              </span>
            </Link>
            <button type="button" onClick={() => void logout()} className="btn-quiet">
              Sign out
            </button>
          </div>
        </header>
        <main className="app-main text-ink">
          <PageStage />
        </main>
      </div>
    </div>
  );
}
