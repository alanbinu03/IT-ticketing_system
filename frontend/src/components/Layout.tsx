import { useEffect, useState } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../lib/auth";
import { ThemeSwitcher } from "./ThemeSwitcher";
import { NotificationBell } from "./NotificationBell";
import { Avatar } from "./ui";

const linkClass = ({ isActive }: { isActive: boolean }) =>
  `block rounded-xl px-3 py-2 text-sm transition ${
    isActive ? "bg-sidebar-active text-white shadow-sm" : "text-sidebar-muted hover:bg-sidebar-hover hover:text-white"
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
  "/admin/users": "Users",
  "/admin/roles": "Roles",
  "/admin/departments": "Departments",
  "/admin/teams": "Teams",
};

function pageTitle(pathname: string): string {
  if (TITLES[pathname]) return TITLES[pathname];
  if (pathname.startsWith("/tickets/")) return "Ticket";
  return "Workspace";
}

export function AppLayout() {
  const location = useLocation();
  const { user, logout, hasPermission } = useAuth();
  const [navOpen, setNavOpen] = useState(false);
  const showAdmin =
    hasPermission("user.view") ||
    hasPermission("role.manage") ||
    hasPermission("department.manage") ||
    hasPermission("team.manage");

  useEffect(() => {
    setNavOpen(false);
  }, [location.pathname]);

  return (
    <div className="app-shell lg:grid lg:grid-cols-[250px_1fr] lg:gap-3">
      {navOpen && <button type="button" className="app-scrim" aria-label="Close menu" onClick={() => setNavOpen(false)} />}
      <aside className={`app-sidebar overflow-y-auto px-4 py-6 ${navOpen ? "is-open" : ""}`}>
        <NavLink to="/dashboard" className="nav-brand px-3">
          <p className="text-xs uppercase tracking-[0.2em] text-sidebar-muted">Internal</p>
          <h1 className="mt-1 text-lg font-semibold tracking-tight">IT Ticketing</h1>
        </NavLink>
        <nav className="mt-8 space-y-1">
          <NavLink to="/dashboard" className={linkClass}>
            Dashboard
          </NavLink>
          <NavLink to="/tickets" className={linkClass}>
            Tickets
          </NavLink>
          {hasPermission("ticket.view_all") && (
            <>
              <p className="px-3 pt-6 pb-2 text-xs uppercase tracking-[0.18em] text-sidebar-muted">Queues</p>
              <NavLink to="/agent/my-queue" className={linkClass}>
                Assigned to me
              </NavLink>
              <NavLink to="/agent/unassigned" className={linkClass}>
                Unassigned
              </NavLink>
            </>
          )}
          <NavLink to="/profile" className={linkClass}>
            Profile
          </NavLink>
          {showAdmin && (
            <>
              <p className="px-3 pt-6 pb-2 text-xs uppercase tracking-[0.18em] text-sidebar-muted">
                Administration
              </p>
              {hasPermission("user.view") && (
                <NavLink to="/admin/users" className={linkClass}>
                  Users
                </NavLink>
              )}
              {hasPermission("role.manage") && (
                <NavLink to="/admin/roles" className={linkClass}>
                  Roles
                </NavLink>
              )}
              {hasPermission("department.manage") && (
                <NavLink to="/admin/departments" className={linkClass}>
                  Departments
                </NavLink>
              )}
              {hasPermission("team.manage") && (
                <NavLink to="/admin/teams" className={linkClass}>
                  Teams
                </NavLink>
              )}
            </>
          )}
        </nav>
      </aside>
      <div className="app-content">
        <header className="app-header flex items-center justify-between gap-3 border-b border-edge px-4 py-3 sm:px-6">
          <div className="flex min-w-0 items-center gap-3">
            <button type="button" className="icon-btn lg:hidden" onClick={() => setNavOpen(true)}>
              Menu
            </button>
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold">{pageTitle(location.pathname)}</p>
              <p className="hidden text-xs text-muted sm:block">
                {hasPermission("ticket.view_all")
                  ? "Assign work and keep the queue moving"
                  : "Track your requests and updates"}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2 sm:gap-3">
            {hasPermission("ticket.view_all") && <NotificationBell />}
            <ThemeSwitcher />
            <Link to="/profile" className="hidden items-center gap-2 rounded-xl px-1 py-0.5 hover:bg-accent-soft sm:flex">
              <Avatar name={user?.full_name} size="sm" />
              <span className="text-right">
                <p className="text-sm font-medium leading-tight">{user?.full_name}</p>
                <p className="text-xs text-muted">{user?.roles.join(", ")}</p>
              </span>
            </Link>
            <button type="button" onClick={() => void logout()} className="btn-secondary">
              Sign out
            </button>
          </div>
        </header>
        <main className="app-main text-ink">
          <div key={location.pathname} className="page-enter">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
