import type { ReactElement } from "react";
import { Navigate } from "react-router-dom";
import { hasValidSession } from "../api/client";

export default function RequireAuth({ children }: { children: ReactElement }) {
  if (!hasValidSession()) return <Navigate to="/login" replace />;
  return children;
}
