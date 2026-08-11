import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import type { RoleName } from "../types";

interface ProtectedRouteProps {
  allowedRoles?: RoleName[];
}

export function ProtectedRoute({ allowedRoles }: ProtectedRouteProps) {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return <div className="p-8 text-center text-gray-500">Loading…</div>;
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (allowedRoles && !allowedRoles.includes(user.role)) {
    // Section 2: employee never even sees modules they don't have access to.
    return <Navigate to="/" replace />;
  }

  return <Outlet />;
}
