import { Navigate } from "react-router-dom";
import type { RouteObject } from "react-router-dom";

import { AppLayout } from "../components/layout/AppLayout";
import { ProcessingHealthPage } from "../features/processing-health/pages/ProcessingHealthPage";
import { NotFoundPage } from "./NotFoundPage";

export const appRoutes: RouteObject[] = [
  {
    path: "/",
    element: <AppLayout />,
    children: [
      { index: true, element: <Navigate to="/processing-health" replace /> },
      { path: "processing-health", element: <ProcessingHealthPage /> },
      { path: "*", element: <NotFoundPage /> },
    ],
  },
];
