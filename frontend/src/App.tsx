import { Navigate, Route, Routes } from "react-router-dom";
import { AppLayout } from "./components/Layout";
import { PageAmbient } from "./components/PageAmbient";
import { AdminProtectedRoute, ProtectedRoute } from "./components/ProtectedRoute";
import { AdminLoginPage } from "./views/AdminLoginPage";
import { DashboardPage } from "./views/DashboardPage";
import { LoginPage } from "./views/LoginPage";
import { NewTicketPage } from "./views/NewTicketPage";
import { ProfilePage } from "./views/ProfilePage";
import { TicketDetailPage } from "./views/TicketDetailPage";
import { TicketsPage } from "./views/TicketsPage";
import { DepartmentsPage } from "./views/admin/DepartmentsPage";
import { UsersPage } from "./views/admin/UsersPage";
import { MyQueuePage, UnassignedQueuePage, CompletedQueuePage } from "./views/agent/QueuePages";

export default function App() {
  return (
    <>
      <PageAmbient />
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<Navigate to="/login" replace />} />
        <Route path="/admin/login" element={<AdminLoginPage />} />

        <Route
          element={
            <ProtectedRoute>
              <AppLayout />
            </ProtectedRoute>
          }
        >
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/tickets" element={<TicketsPage title="Tickets" />} />
          <Route path="/tickets/new" element={<NewTicketPage />} />
          <Route path="/tickets/:id" element={<TicketDetailPage />} />
          <Route path="/profile" element={<ProfilePage />} />
          <Route
            path="/agent/my-queue"
            element={
              <ProtectedRoute permission="ticket.view_all">
                <MyQueuePage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/agent/unassigned"
            element={
              <ProtectedRoute permission="ticket.view_all">
                <UnassignedQueuePage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/agent/completed"
            element={
              <ProtectedRoute permission="ticket.view_all">
                <CompletedQueuePage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/users"
            element={
              <ProtectedRoute permission="user.view">
                <UsersPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin/departments"
            element={
              <ProtectedRoute permission="department.manage">
                <DepartmentsPage />
              </ProtectedRoute>
            }
          />
        </Route>

        <Route
          element={
            <AdminProtectedRoute>
              <AppLayout />
            </AdminProtectedRoute>
          }
        >
          <Route path="/admin/dashboard" element={<DashboardPage />} />
        </Route>

        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </>
  );
}
