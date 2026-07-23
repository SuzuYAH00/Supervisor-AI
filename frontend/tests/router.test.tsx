import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { RouterProvider, createMemoryRouter } from "react-router-dom";

import { appRoutes } from "../src/app/routes";
import { getCommercialEvents } from "../src/features/commercial-events/api/get-commercial-events";
import { getFinancialSummary } from "../src/features/financial-summary/api/get-financial-summary";
import { getFinancialTimeline } from "../src/features/financial-timeline/api/get-financial-timeline";
import { getProcessingHealth } from "../src/features/processing-health/api/get-processing-health";
import { getProcessingRuns } from "../src/features/processing-runs/api/get-processing-runs";
import { getProcessingRunDetail } from "../src/features/processing-runs/api/get-processing-run-detail";
import {
  commercialEvents,
  financialSummary,
  processingHealth,
  processingRuns,
  processingRunDetail,
} from "./fixtures";

vi.mock(
  "../src/features/processing-health/api/get-processing-health",
  () => ({ getProcessingHealth: vi.fn() }),
);
vi.mock(
  "../src/features/processing-runs/api/get-processing-runs",
  () => ({ getProcessingRuns: vi.fn() }),
);
vi.mock(
  "../src/features/processing-runs/api/get-processing-run-detail",
  () => ({ getProcessingRunDetail: vi.fn() }),
);
vi.mock(
  "../src/features/financial-timeline/api/get-financial-timeline",
  () => ({ getFinancialTimeline: vi.fn() }),
);
vi.mock(
  "../src/features/commercial-events/api/get-commercial-events",
  () => ({ getCommercialEvents: vi.fn() }),
);
vi.mock(
  "../src/features/financial-summary/api/get-financial-summary",
  () => ({ getFinancialSummary: vi.fn() }),
);

const getProcessingHealthMock = vi.mocked(getProcessingHealth);
const getFinancialSummaryMock = vi.mocked(getFinancialSummary);
const getCommercialEventsMock = vi.mocked(getCommercialEvents);
const getFinancialTimelineMock = vi.mocked(getFinancialTimeline);
const getProcessingRunsMock = vi.mocked(getProcessingRuns);
const getProcessingRunDetailMock = vi.mocked(getProcessingRunDetail);

function renderRoute(path: string) {
  return render(
    <RouterProvider
      router={createMemoryRouter(appRoutes, { initialEntries: [path] })}
    />,
  );
}

test("root redirects to the processing health page", async () => {
  getProcessingHealthMock.mockResolvedValue(processingHealth());
  renderRoute("/");
  expect(await screen.findByText("Saúde do processamento")).toBeInTheDocument();
});

test("processing health route renders inside the operational layout", async () => {
  getProcessingHealthMock.mockResolvedValue(processingHealth());
  renderRoute("/processing-health");
  expect(await screen.findByText("Saúde do processamento")).toBeInTheDocument();
  expect(screen.getByText("MVP interno")).toBeInTheDocument();
  expect(screen.getByRole("navigation")).toBeInTheDocument();
  expect(
    screen.getByRole("link", { name: "Supervisor AI" }),
  ).toHaveAttribute("href", "/processing-health");
});

test("financial navigation opens the summary through React Router", async () => {
  const user = userEvent.setup();
  getProcessingHealthMock.mockResolvedValue(processingHealth());
  getFinancialSummaryMock.mockResolvedValue(financialSummary());
  renderRoute("/processing-health");

  await user.click(
    await screen.findByRole("link", { name: /Resumo Financeiro/ }),
  );
  expect(await screen.findByText("Resumo financeiro")).toBeInTheDocument();
  expect(
    screen.getByRole("link", { name: /Resumo Financeiro/ }),
  ).toHaveAttribute("href", "/financial-summary");
});

test("financial summary route renders directly", async () => {
  getFinancialSummaryMock.mockResolvedValue(financialSummary());
  renderRoute("/financial-summary");
  expect(await screen.findByText("Resumo financeiro")).toBeInTheDocument();
  expect(screen.getByText("MVP interno")).toBeInTheDocument();
});

test("commercial events navigation opens the list through React Router", async () => {
  const user = userEvent.setup();
  getProcessingHealthMock.mockResolvedValue(processingHealth());
  getCommercialEventsMock.mockResolvedValue(commercialEvents());
  renderRoute("/processing-health");

  await user.click(
    await screen.findByRole("link", { name: /Eventos comerciais/ }),
  );
  expect(await screen.findByText("Eventos persistidos")).toBeInTheDocument();
  expect(
    screen.getByRole("link", { name: /Eventos comerciais/ }),
  ).toHaveAttribute("href", "/commercial-events");
});

test("commercial events route renders directly", async () => {
  getCommercialEventsMock.mockResolvedValue(commercialEvents());
  renderRoute("/commercial-events");
  expect(await screen.findByText("Eventos persistidos")).toBeInTheDocument();
  expect(screen.getByText("MVP interno")).toBeInTheDocument();
});

test("financial timeline navigation uses React Router and starts idle", async () => {
  const user = userEvent.setup();
  getProcessingHealthMock.mockResolvedValue(processingHealth());
  renderRoute("/processing-health");
  await user.click(
    await screen.findByRole("link", { name: /Timeline financeira/ }),
  );

  expect(
    screen.getByText("Informe um colaborador para iniciar a consulta."),
  ).toBeInTheDocument();
  expect(getFinancialTimelineMock).not.toHaveBeenCalled();
  expect(
    screen.getByRole("link", { name: /Timeline financeira/ }),
  ).toHaveAttribute("href", "/financial-timeline");
});

test("financial timeline route renders directly without querying", () => {
  renderRoute("/financial-timeline");
  expect(screen.getByRole("heading", { name: "Timeline financeira" })).toBeInTheDocument();
  expect(getFinancialTimelineMock).not.toHaveBeenCalled();
});

test("processing runs navigation opens the list through React Router", async () => {
  const user = userEvent.setup();
  getProcessingHealthMock.mockResolvedValue(processingHealth());
  getProcessingRunsMock.mockResolvedValue(processingRuns());
  renderRoute("/processing-health");

  await user.click(
    await screen.findByRole("link", { name: /Execuções de processamento/ }),
  );
  expect(
    await screen.findByRole("heading", { name: "Execuções de processamento" }),
  ).toBeInTheDocument();
  expect(
    screen.getByRole("link", { name: /Execuções de processamento/ }),
  ).toHaveAttribute("href", "/processing-runs");
});

test("processing runs route renders directly", async () => {
  getProcessingRunsMock.mockResolvedValue(processingRuns());
  renderRoute("/processing-runs");
  expect(
    await screen.findByRole("heading", { name: "Execuções de processamento" }),
  ).toBeInTheDocument();
  expect(screen.getByText("MVP interno")).toBeInTheDocument();
});

test("processing run link opens the detail through React Router", async () => {
  const user = userEvent.setup();
  getProcessingRunsMock.mockResolvedValue(processingRuns());
  getProcessingRunDetailMock.mockResolvedValue(processingRunDetail());
  renderRoute("/processing-runs");

  await user.click(await screen.findByRole("link", { name: "run-2" }));
  expect(
    await screen.findByRole("heading", { name: "Detalhes da execução" }),
  ).toBeInTheDocument();
  expect(getProcessingRunDetailMock).toHaveBeenCalledWith(
    "run-2",
    expect.any(AbortSignal),
  );
});

test("processing run detail renders directly and returns to the list", async () => {
  const user = userEvent.setup();
  getProcessingRunDetailMock.mockResolvedValue(processingRunDetail());
  getProcessingRunsMock.mockResolvedValue(processingRuns());
  renderRoute("/processing-runs/run-1");

  expect(
    await screen.findByRole("heading", { name: "Detalhes da execução" }),
  ).toBeInTheDocument();
  await user.click(
    screen.getByRole("link", { name: "Voltar para execuções" }),
  );
  expect(
    await screen.findByRole("heading", { name: "Execuções de processamento" }),
  ).toBeInTheDocument();
});

test("unknown route returns to processing health through client navigation", async () => {
  const user = userEvent.setup();
  getProcessingHealthMock.mockResolvedValue(processingHealth());
  renderRoute("/unknown");
  expect(screen.getByText("Este endereço não existe")).toBeInTheDocument();
  await user.click(screen.getByRole("link", { name: "Ir para visão geral" }));
  expect(await screen.findByText("Saúde do processamento")).toBeInTheDocument();
});
