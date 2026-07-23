import { Navigate } from "react-router-dom";
import type { RouteObject } from "react-router-dom";

import { AppLayout } from "../components/layout/AppLayout";
import { CommercialEventsPage } from "../features/commercial-events/pages/CommercialEventsPage";
import { CommercialEventDetailPage } from "../features/commercial-events/pages/CommercialEventDetailPage";
import { FinancialSummaryPage } from "../features/financial-summary/pages/FinancialSummaryPage";
import { FinancialTimelinePage } from "../features/financial-timeline/pages/FinancialTimelinePage";
import { ProcessingHealthPage } from "../features/processing-health/pages/ProcessingHealthPage";
import { ProcessingRunDetailPage } from "../features/processing-runs/pages/ProcessingRunDetailPage";
import { ProcessingRunsPage } from "../features/processing-runs/pages/ProcessingRunsPage";
import { NotFoundPage } from "./NotFoundPage";

export const appRoutes: RouteObject[] = [
  {
    path: "/",
    element: <AppLayout />,
    children: [
      { index: true, element: <Navigate to="/processing-health" replace /> },
      { path: "processing-health", element: <ProcessingHealthPage /> },
      { path: "financial-summary", element: <FinancialSummaryPage /> },
      { path: "commercial-events", element: <CommercialEventsPage /> },
      {
        path: "commercial-events/:commercialEventId",
        element: <CommercialEventDetailPage />,
      },
      { path: "financial-timeline", element: <FinancialTimelinePage /> },
      { path: "processing-runs", element: <ProcessingRunsPage /> },
      {
        path: "processing-runs/:processingRunId",
        element: <ProcessingRunDetailPage />,
      },
      { path: "*", element: <NotFoundPage /> },
    ],
  },
];
