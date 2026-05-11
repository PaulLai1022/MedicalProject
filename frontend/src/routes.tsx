import { createBrowserRouter } from "react-router-dom";
import { AppShell } from "@/components/layout/AppShell";
import { ProtectedRoute } from "@/components/layout/ProtectedRoute";
import { LoginPage } from "@/pages/LoginPage";
import { RegisterPage } from "@/pages/RegisterPage";
import { HomePage } from "@/pages/HomePage";
import { CaseListPage } from "@/pages/CaseListPage";
import { CaseDetailPage } from "@/pages/CaseDetailPage";

export const router = createBrowserRouter([
  { path: "/login", element: <LoginPage /> },
  { path: "/register", element: <RegisterPage /> },
  {
    element: <ProtectedRoute />,
    children: [
      {
        element: <AppShell />,
        children: [
          { path: "/", element: <HomePage /> },
          { path: "/cases", element: <CaseListPage /> },
          { path: "/cases/:id", element: <CaseDetailPage /> },
        ],
      },
    ],
  },
]);
