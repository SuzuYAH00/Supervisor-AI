import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { getFinancialTimeline } from "../src/features/financial-timeline/api/get-financial-timeline";
import { FinancialTimelinePage } from "../src/features/financial-timeline/pages/FinancialTimelinePage";
import { ApiError } from "../src/lib/http/api-error";
import { financialTimeline } from "./fixtures";

vi.mock(
  "../src/features/financial-timeline/api/get-financial-timeline",
  () => ({ getFinancialTimeline: vi.fn() }),
);

const getFinancialTimelineMock = vi.mocked(getFinancialTimeline);

async function submitCollaborator(value: string) {
  const user = userEvent.setup();
  await user.type(
    screen.getByRole("textbox", { name: "Identificador do colaborador" }),
    value,
  );
  await user.click(screen.getByRole("button", { name: "Consultar timeline" }));
  return user;
}

test("starts idle and blocks an empty submission with an accessible error", async () => {
  const user = userEvent.setup();
  render(<FinancialTimelinePage />);
  expect(
    screen.getByText("Informe um colaborador para iniciar a consulta."),
  ).toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: "Consultar timeline" }));
  expect(
    screen.getByText("Informe um identificador de colaborador."),
  ).toHaveAttribute("role", "alert");
  expect(getFinancialTimelineMock).not.toHaveBeenCalled();
});

test("trims outer whitespace, preserves case and supports Enter", async () => {
  const user = userEvent.setup();
  getFinancialTimelineMock.mockResolvedValue(financialTimeline());
  render(<FinancialTimelinePage />);

  const input = screen.getByRole("textbox", {
    name: "Identificador do colaborador",
  });
  await user.type(input, "  Employee-A  {Enter}");
  expect(await screen.findByText("Lançamentos financeiros")).toBeInTheDocument();
  expect(getFinancialTimelineMock).toHaveBeenCalledWith(
    "Employee-A",
    {},
    expect.any(AbortSignal),
  );
});

test("shows loading and every factual Ledger field without totals", async () => {
  let resolveRequest: (value: ReturnType<typeof financialTimeline>) => void =
    () => undefined;
  getFinancialTimelineMock.mockReturnValue(
    new Promise((resolve) => {
      resolveRequest = resolve;
    }),
  );
  render(<FinancialTimelinePage />);
  await submitCollaborator("Employee-A");
  expect(
    screen.getByText("Carregando timeline de Employee-A"),
  ).toBeInTheDocument();
  resolveRequest(financialTimeline());

  const row = await screen.findByRole("row", {
    name: /ledger-1 2026-07-22T12:05:00Z credit BRL 99.90/,
  });
  expect(within(row).getByText("99.90")).toBeInTheDocument();
  expect(within(row).getByText("posting:event-1")).toBeInTheDocument();
  expect(within(row).getByText("calculation:event-1")).toBeInTheDocument();
  expect(within(row).getByText("invoice-1, ticket-1")).toBeInTheDocument();
  expect(within(row).getByText("event-1")).toBeInTheDocument();
  expect(screen.queryByText(/saldo/i)).not.toBeInTheDocument();
  expect(screen.queryByText(/total/i)).not.toBeInTheDocument();
});

test("treats a collaborator without entries as an empty success", async () => {
  getFinancialTimelineMock.mockResolvedValue(
    financialTimeline({ collaborator_id: "unknown", items: [] }),
  );
  render(<FinancialTimelinePage />);
  await submitCollaborator("unknown");
  expect(
    await screen.findByText("Nenhum lançamento financeiro foi encontrado."),
  ).toBeInTheDocument();
  expect(screen.getByText(/consulta de unknown foi concluída/)).toBeInTheDocument();
});

test("treats HTTP 404 generically and retries the same collaborator", async () => {
  const user = userEvent.setup();
  getFinancialTimelineMock
    .mockRejectedValueOnce(
      new ApiError({
        status: 404,
        code: "unexpected_api_error",
        message: "O Supervisor AI não pôde concluir a solicitação.",
        kind: "invalid-response",
      }),
    )
    .mockResolvedValueOnce(financialTimeline());
  render(<FinancialTimelinePage />);
  await submitCollaborator("Employee-A");

  expect(
    await screen.findByText("A consulta não pôde ser concluída"),
  ).toBeInTheDocument();
  expect(
    screen.queryByText("Colaborador não encontrado"),
  ).not.toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Tentar novamente" }));
  expect(await screen.findByText("Lançamentos financeiros")).toBeInTheDocument();
  expect(getFinancialTimelineMock).toHaveBeenLastCalledWith(
    "Employee-A",
    {},
    expect.any(AbortSignal),
  );
});

test("shows safe errors and retries the current request", async () => {
  const user = userEvent.setup();
  getFinancialTimelineMock
    .mockRejectedValueOnce(
      new ApiError({
        code: "network_error",
        message: "Não foi possível conectar ao Supervisor AI.",
        kind: "network",
      }),
    )
    .mockResolvedValueOnce(financialTimeline());
  render(<FinancialTimelinePage />);
  await submitCollaborator("Employee-A");

  expect(await screen.findByText("O backend está indisponível")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Tentar novamente" }));
  expect(await screen.findByText("Lançamentos financeiros")).toBeInTheDocument();
});

test("navigates pages, retries the requested cursor and returns through history", async () => {
  const user = userEvent.setup();
  getFinancialTimelineMock
    .mockResolvedValueOnce(
      financialTimeline({
        page: { limit: 1, next_cursor: "page-2", has_more: true },
      }),
    )
    .mockRejectedValueOnce(
      new ApiError({
        code: "network_error",
        message: "Não foi possível conectar ao Supervisor AI.",
        kind: "network",
      }),
    )
    .mockResolvedValueOnce(
      financialTimeline({
        page: { limit: 1, next_cursor: null, has_more: false },
        items: [{ ...financialTimeline().items[0]!, ledger_entry_id: "ledger-2" }],
      }),
    )
    .mockResolvedValueOnce(
      financialTimeline({
        page: { limit: 1, next_cursor: "page-2", has_more: true },
      }),
    );
  render(<FinancialTimelinePage />);
  await submitCollaborator("Employee-A");

  const next = await screen.findByRole("button", { name: "Próxima página" });
  expect(next).toBeEnabled();
  await user.click(next);
  expect(await screen.findByText("O backend está indisponível")).toBeInTheDocument();
  expect(screen.queryByText("ledger-1")).not.toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Tentar novamente" }));
  expect(await screen.findByText("ledger-2")).toBeInTheDocument();
  expect(screen.getByText("Página 2 desta consulta")).toBeInTheDocument();
  expect(
    screen.getByRole("button", { name: "Próxima página" }),
  ).toBeDisabled();
  expect(getFinancialTimelineMock).toHaveBeenNthCalledWith(
    3,
    "Employee-A",
    { cursor: "page-2" },
    expect.any(AbortSignal),
  );

  await user.click(screen.getByRole("button", { name: "Página anterior" }));
  expect(await screen.findByText("ledger-1")).toBeInTheDocument();
  expect(screen.getByText("Página 1 desta consulta")).toBeInTheDocument();
});

test("a new collaborator resets data and cursor history", async () => {
  const user = userEvent.setup();
  getFinancialTimelineMock
    .mockResolvedValueOnce(
      financialTimeline({
        page: { limit: 1, next_cursor: "page-2", has_more: true },
      }),
    )
    .mockResolvedValueOnce(
      financialTimeline({
        collaborator_id: "Employee-B",
        items: [{ ...financialTimeline().items[0]!, ledger_entry_id: "ledger-B" }],
      }),
    );
  render(<FinancialTimelinePage />);
  await submitCollaborator("Employee-A");
  expect(await screen.findByText("ledger-1")).toBeInTheDocument();

  const input = screen.getByRole("textbox", {
    name: "Identificador do colaborador",
  });
  await user.clear(input);
  await user.type(input, "Employee-B");
  await user.click(screen.getByRole("button", { name: "Consultar timeline" }));
  expect(screen.queryByText("ledger-1")).not.toBeInTheDocument();
  expect(await screen.findByText("ledger-B")).toBeInTheDocument();
  expect(screen.getByText("Página 1 desta consulta")).toBeInTheDocument();
  expect(
    screen.getByRole("button", { name: "Página anterior" }),
  ).toBeDisabled();
});

test("stale responses cannot replace a newer collaborator result", async () => {
  let resolveA: (value: ReturnType<typeof financialTimeline>) => void =
    () => undefined;
  let resolveB: (value: ReturnType<typeof financialTimeline>) => void =
    () => undefined;
  const signals: AbortSignal[] = [];
  getFinancialTimelineMock
    .mockImplementationOnce((_id, _query, signal) => {
      if (signal !== undefined) {
        signals.push(signal);
      }
      return new Promise((resolve) => {
        resolveA = resolve;
      });
    })
    .mockImplementationOnce((_id, _query, signal) => {
      if (signal !== undefined) {
        signals.push(signal);
      }
      return new Promise((resolve) => {
        resolveB = resolve;
      });
    });
  render(<FinancialTimelinePage />);
  const user = await submitCollaborator("Employee-A");

  const input = screen.getByRole("textbox", {
    name: "Identificador do colaborador",
  });
  await user.clear(input);
  await user.type(input, "Employee-B");
  await user.click(screen.getByRole("button", { name: "Consultar timeline" }));
  expect(signals[0]?.aborted).toBe(true);

  resolveB(
    financialTimeline({
      collaborator_id: "Employee-B",
      items: [{ ...financialTimeline().items[0]!, ledger_entry_id: "ledger-B" }],
    }),
  );
  expect(await screen.findByText("ledger-B")).toBeInTheDocument();
  resolveA(financialTimeline());
  await waitFor(() =>
    expect(screen.queryByText("ledger-1")).not.toBeInTheDocument(),
  );
});

test("unmount aborts the active request", async () => {
  let signal: AbortSignal | undefined;
  getFinancialTimelineMock.mockImplementation((_id, _query, requestSignal) => {
    signal = requestSignal;
    return new Promise(() => undefined);
  });
  const view = render(<FinancialTimelinePage />);
  await submitCollaborator("Employee-A");
  expect(signal?.aborted).toBe(false);
  view.unmount();
  expect(signal?.aborted).toBe(true);
});
