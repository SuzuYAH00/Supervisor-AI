import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { getFinancialSummary } from "../src/features/financial-summary/api/get-financial-summary";
import { FinancialSummaryPage } from "../src/features/financial-summary/pages/FinancialSummaryPage";
import { ApiError } from "../src/lib/http/api-error";
import { financialSummary } from "./fixtures";

vi.mock(
  "../src/features/financial-summary/api/get-financial-summary",
  () => ({ getFinancialSummary: vi.fn() }),
);

const getFinancialSummaryMock = vi.mocked(getFinancialSummary);

test("announces loading then renders totals and collaborator rows", async () => {
  let resolveRequest: (value: ReturnType<typeof financialSummary>) => void =
    () => undefined;
  getFinancialSummaryMock.mockReturnValue(
    new Promise((resolve) => {
      resolveRequest = resolve;
    }),
  );

  render(<FinancialSummaryPage />);
  expect(screen.getByText("Carregando resumo financeiro")).toBeInTheDocument();
  resolveRequest(financialSummary());

  expect(await screen.findByText("Resumo financeiro")).toBeInTheDocument();
  const metrics = screen.getByRole("region", { name: "Resumo geral" });
  const creditsCard = within(metrics).getByText("Créditos").closest("article");
  if (creditsCard === null) {
    throw new Error("Credits metric card was not rendered");
  }
  expect(within(creditsCard).getByText("3")).toBeInTheDocument();
  expect(screen.getByText("BRL 219.80")).toBeInTheDocument();
  expect(screen.getByText("USD 10.00")).toBeInTheDocument();
  expect(screen.getByText("employee-1")).toBeInTheDocument();
  expect(screen.getByText("employee-2")).toBeInTheDocument();
  const employeeOneRow = screen.getByRole("row", {
    name: "employee-1 BRL 219.80 2 4 37.25%",
  });
  expect(within(employeeOneRow).getByText("2")).toBeInTheDocument();
  expect(within(employeeOneRow).getByText("4")).toBeInTheDocument();
  expect(within(employeeOneRow).getByText("37.25%")).toBeInTheDocument();
  const employeeTwoRow = screen.getByRole("row", {
    name: "employee-2 USD 10.00 1 9 12.50%",
  });
  expect(within(employeeTwoRow).getByText("9")).toBeInTheDocument();
  expect(within(employeeTwoRow).getByText("12.50%")).toBeInTheDocument();
  expect(screen.queryByText(/produtividade/i)).not.toBeInTheDocument();
  expect(screen.queryByText(/tendência/i)).not.toBeInTheDocument();
});

test("renders an empty Ledger as a successful operational state", async () => {
  getFinancialSummaryMock.mockResolvedValue(
    financialSummary({
      collaborator_count: 0,
      credit_count: 0,
      totals_by_currency: [],
      collaborators: [],
    }),
  );
  render(<FinancialSummaryPage />);

  expect(
    await screen.findByText("Ainda não existem créditos persistidos."),
  ).toBeInTheDocument();
  expect(
    screen.getByText("Nenhum colaborador com créditos persistidos."),
  ).toBeInTheDocument();
  expect(
    screen.getByText("Nenhum valor financeiro disponível."),
  ).toBeInTheDocument();
});

test("renders a safe error and retries the query", async () => {
  const user = userEvent.setup();
  getFinancialSummaryMock
    .mockRejectedValueOnce(
      new ApiError({
        code: "network_error",
        message: "Não foi possível conectar ao Supervisor AI.",
        kind: "network",
      }),
    )
    .mockResolvedValueOnce(financialSummary());

  render(<FinancialSummaryPage />);
  expect(await screen.findByText("O backend está indisponível")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Tentar novamente" }));
  await waitFor(() => expect(getFinancialSummaryMock).toHaveBeenCalledTimes(2));
  expect(await screen.findByText("Resumo financeiro")).toBeInTheDocument();
});

test("aborts the active request when the page unmounts", () => {
  let receivedSignal: AbortSignal | undefined;
  getFinancialSummaryMock.mockImplementation((_filters, signal) => {
    receivedSignal = signal;
    return new Promise(() => undefined);
  });

  const view = render(<FinancialSummaryPage />);
  expect(receivedSignal?.aborted).toBe(false);
  view.unmount();
  expect(receivedSignal?.aborted).toBe(true);
});
