import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { lazy, Suspense, type ReactNode } from "react";
import { createBrowserRouter, RouterProvider } from "react-router-dom";
import { AppShell } from "./components/AppShell";
import { LoadingState } from "./components/ui";
import { AppProvider } from "./context/AppContext";

const DashboardPage = lazy(() => import("./pages/DashboardPage").then((module) => ({ default: module.DashboardPage })));
const RegulationsPage = lazy(() => import("./pages/RegulationsPage").then((module) => ({ default: module.RegulationsPage })));
const RegulationDetailPage = lazy(() => import("./pages/RegulationDetailPage").then((module) => ({ default: module.RegulationDetailPage })));
const QaPage = lazy(() => import("./pages/QaPage").then((module) => ({ default: module.QaPage })));
const OntologyPage = lazy(() => import("./pages/OntologyPage").then((module) => ({ default: module.OntologyPage })));
const AdminIngestionsPage = lazy(() => import("./pages/AdminIngestionsPage").then((module) => ({ default: module.AdminIngestionsPage })));
const NotFoundPage = lazy(() => import("./pages/NotFoundPage").then((module) => ({ default: module.NotFoundPage })));

function lazyPage(page: ReactNode) {
  return <Suspense fallback={<div className="page"><LoadingState label="화면을 준비하고 있습니다." /></div>}>{page}</Suspense>;
}

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: { staleTime: 30_000, retry: 1, refetchOnWindowFocus: false },
    mutations: { retry: false },
  },
});

const routerBasename = import.meta.env.BASE_URL.replace(/\/$/, "") || "/";

const router = createBrowserRouter(
  [
    {
      path: "/",
      element: <AppShell />,
      children: [
        { index: true, element: lazyPage(<DashboardPage />) },
        { path: "regulations", element: lazyPage(<RegulationsPage />) },
        { path: "regulations/:documentId", element: lazyPage(<RegulationDetailPage />) },
        { path: "regulations/:documentId/versions/:versionId", element: lazyPage(<RegulationDetailPage />) },
        { path: "qa", element: lazyPage(<QaPage />) },
        { path: "ontology", element: lazyPage(<OntologyPage />) },
        { path: "admin/ingestions", element: lazyPage(<AdminIngestionsPage />) },
        { path: "*", element: lazyPage(<NotFoundPage />) },
      ],
    },
  ],
  { basename: routerBasename },
);

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AppProvider>
        <RouterProvider router={router} />
      </AppProvider>
    </QueryClientProvider>
  );
}
