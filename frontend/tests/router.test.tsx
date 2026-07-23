import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { RouterProvider, createMemoryRouter } from "react-router-dom";

import { appRoutes } from "../src/app/routes";
import { getFinancialSummary } from "../src/features/financial-summary/api/get-financial-summary";
import { getProcessingHealth } from "../src/features/processing-health/api/get-processing-health";
import { financialSummary, processingHealth } from "./fixtures";

vi.mock(
  "../src/features/processing-health/api/get-processing-health",
  () => ({ getProcessingHealth: vi.fn() }),
);
vi.mock(
  "../src/features/financial-summary/api/get-financial-summary",
  () => ({ getFinancialSummary: vi.fn() }),
);

const getProcessingHealthMock = vi.mocked(getProcessingHealth);
const getFinancialSummaryMock = vi.mocked(getFinancialSummary);

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

test("unknown route returns to processing health through client navigation", async () => {
  const user = userEvent.setup();
  getProcessingHealthMock.mockResolvedValue(processingHealth());
  renderRoute("/unknown");
  expect(screen.getByText("Este endereço não existe")).toBeInTheDocument();
  await user.click(screen.getByRole("link", { name: "Ir para visão geral" }));
  expect(await screen.findByText("Saúde do processamento")).toBeInTheDocument();
});
