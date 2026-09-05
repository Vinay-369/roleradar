import { Navigate } from "react-router-dom";

/**
 * Saved Roles now powers the unified Application Tracker (Part 6 & 16).
 * Automatically routes the student to the "Saved" tab within Applications
 * to avoid duplicate screens and fractured application state.
 */
export function Saved() {
  return <Navigate to="/applications?tab=SAVED" replace />;
}
