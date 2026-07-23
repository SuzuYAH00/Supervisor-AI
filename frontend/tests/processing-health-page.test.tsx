import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { ProcessingHealthPage } from "../src/features/processing-health/pages/ProcessingHealthPage";
import { ApiError } from "../src/lib/http/api-error";
import { getProcessingHealth } from "../src/features/processing-health/api/get-processing-health";
import { processingHealth } from "./fixtures";

vi.mock(
  "../src/features/processing-health/api/get-processing-health",
  () => ({ getProcessingHealth: vi.fn() }),
);

const getProcessingHealthMock = vi.mocked(getProcessingHealth);

test("announces loading then renders factual metrics and ordered distributions", async () => {
  let resolveRequest: (value: ReturnType<typeof processingHealth>) => void =
    () => undefined;
  getProcessingHealthMock.mockReturnValue(
    new Promise((resolve) => {
      resolveRequest = resolve;
    }),
  );
  render(<ProcessingHealthPage />);
  expect(
    screen.getByText("Carregando saúde do processamento"),
  ).toBeInTheDocument();

  resolveRequest(processingHealth());
  expect(await screen.findByText("Saúde do processamento")).toBeInTheDocument();
  const executionsCard = screen.getByText("Execuções").closest("article");
  if (executionsCard === null) {
    throw new Error("Executions metric card was not rendered");
  }
  expect(within(executionsCard).getByText("3")).toBeInTheDocument();
  expect(screen.getByText("Eventos com Ledger")).toBeInTheDocument();
  expect(screen.getByText("Eventos sem Ledger")).toBeInTheDocument();
  expect(screen.getByText("not_evaluable")).toBeInTheDocument();
  expect(screen.getByText("posted")).toBeInTheDocument();
  expect(screen.getByText("rules-1")).toBeInTheDocument();
  expect(screen.getByText("rules-2")).toBeInTheDocument();
  expect(screen.queryByText(/taxa de sucesso/i)).not.toBeInTheDocument();
  expect(screen.queryByText(/score/i)).not.toBeInTheDocument();
});

test("renders a useful empty database state instead of an error", async () => {
  getProcessingHealthMock.mockResolvedValue(
    processingHealth({
      processing_runs: {
        total: 0,
        by_final_status: [],
        by_rules_engine_version: [],
      },
      commercial_events: {
        events_with_processing_runs: 0,
        events_without_processing_runs: 0,
        events_with_multiple_processing_runs: 0,
        events_with_ledger_entries: 0,
        events_without_ledger_entries: 0,
      },
    }),
  );
  render(<ProcessingHealthPage />);
  expect(
    await screen.findByText("Ainda não existem processamentos persistidos."),
  ).toBeInTheDocument();
  expect(screen.getAllByText("0")).toHaveLength(5);
});

test("renders a safe connection error and retries", async () => {
  const user = userEvent.setup();
  getProcessingHealthMock
    .mockRejectedValueOnce(
      new ApiError({
        code: "network_error",
        message: "Não foi possível conectar ao Supervisor AI.",
        kind: "network",
      }),
    )
    .mockResolvedValueOnce(processingHealth());

  render(<ProcessingHealthPage />);
  expect(await screen.findByText("O backend está indisponível")).toBeInTheDocument();
  expect(screen.queryByText(/stack/i)).not.toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Tentar novamente" }));
  await waitFor(() => expect(getProcessingHealthMock).toHaveBeenCalledTimes(2));
  expect(await screen.findByText("Saúde do processamento")).toBeInTheDocument();
});
