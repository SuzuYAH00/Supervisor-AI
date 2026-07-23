import { act, render, renderHook, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";

import { getProcessingRuns } from "../src/features/processing-runs/api/get-processing-runs";
import { useProcessingRuns } from "../src/features/processing-runs/hooks/use-processing-runs";
import { ProcessingRunsPage } from "../src/features/processing-runs/pages/ProcessingRunsPage";
import { ApiError } from "../src/lib/http/api-error";
import { processingRuns } from "./fixtures";

vi.mock(
  "../src/features/processing-runs/api/get-processing-runs",
  () => ({ getProcessingRuns: vi.fn() }),
);

const getProcessingRunsMock = vi.mocked(getProcessingRuns);

function renderPage() {
  return render(
    <MemoryRouter>
      <ProcessingRunsPage />
    </MemoryRouter>,
  );
}

test("announces loading and projects every factual field", async () => {
  let resolveRequest: (value: ReturnType<typeof processingRuns>) => void =
    () => undefined;
  getProcessingRunsMock.mockReturnValue(
    new Promise((resolve) => {
      resolveRequest = resolve;
    }),
  );
  renderPage();
  expect(screen.getByText("Carregando execuções")).toBeInTheDocument();

  resolveRequest(processingRuns());
  const row = await screen.findByRole("row", {
    name: /run-2 event-2 csv-example external-2/,
  });
  expect(within(row).getByText("posted")).toBeInTheDocument();
  expect(within(row).getByText("rules-1")).toBeInTheDocument();
  expect(within(row).getByRole("link", { name: "run-2" })).toHaveAttribute(
    "href",
    "/processing-runs/run-2",
  );
  expect(within(row).getByText("2026-07-23T14:00:00Z")).toHaveAttribute(
    "datetime",
    "2026-07-23T14:00:00Z",
  );
  expect(screen.queryByText(/duração/i)).not.toBeInTheDocument();
  expect(screen.queryByText(/taxa/i)).not.toBeInTheDocument();
  expect(screen.queryByText(/total geral/i)).not.toBeInTheDocument();
});

test("renders an empty response as success", async () => {
  getProcessingRunsMock.mockResolvedValue(processingRuns({ items: [] }));
  renderPage();

  expect(
    await screen.findByText("Nenhuma execução de processamento foi encontrada."),
  ).toBeInTheDocument();
  expect(
    screen.getByRole("button", { name: "Próxima página" }),
  ).toBeDisabled();
});

test("retries an initial error", async () => {
  const user = userEvent.setup();
  getProcessingRunsMock
    .mockRejectedValueOnce(
      new ApiError({
        code: "network_error",
        message: "Não foi possível conectar ao Supervisor AI.",
        kind: "network",
      }),
    )
    .mockResolvedValueOnce(processingRuns());
  renderPage();

  expect(await screen.findByText("O backend está indisponível")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Tentar novamente" }));
  expect(await screen.findByText("run-2")).toBeInTheDocument();
  expect(getProcessingRunsMock).toHaveBeenLastCalledWith(
    {},
    expect.any(AbortSignal),
  );
});

test("navigates through opaque cursors and returns with local history", async () => {
  const user = userEvent.setup();
  let resolveSecond: (value: ReturnType<typeof processingRuns>) => void =
    () => undefined;
  getProcessingRunsMock
    .mockResolvedValueOnce(processingRuns({ next_cursor: "opaque-page-2" }))
    .mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          resolveSecond = resolve;
        }),
    )
    .mockResolvedValueOnce(processingRuns({ next_cursor: "opaque-page-2" }));
  renderPage();

  await user.click(
    await screen.findByRole("button", { name: "Próxima página" }),
  );
  expect(screen.queryByText("run-2")).not.toBeInTheDocument();
  expect(screen.getByText("Carregando execuções")).toBeInTheDocument();
  resolveSecond(
    processingRuns({
      items: [
        {
          ...processingRuns().items[0],
          processing_run_id: "run-1",
          event_id: "event-1",
        },
      ],
    }),
  );

  expect(await screen.findByText("run-1")).toBeInTheDocument();
  expect(screen.getByText("Página 2 desta sessão")).toBeInTheDocument();
  expect(
    screen.getByRole("button", { name: "Próxima página" }),
  ).toBeDisabled();
  expect(getProcessingRunsMock).toHaveBeenNthCalledWith(
    2,
    { cursor: "opaque-page-2" },
    expect.any(AbortSignal),
  );

  await user.click(screen.getByRole("button", { name: "Página anterior" }));
  expect(await screen.findByText("run-2")).toBeInTheDocument();
});

test("retry on a later page repeats its cursor and back remains available", async () => {
  const user = userEvent.setup();
  getProcessingRunsMock
    .mockResolvedValueOnce(processingRuns({ next_cursor: "failed-page" }))
    .mockRejectedValueOnce(
      new ApiError({
        code: "network_error",
        message: "Não foi possível conectar ao Supervisor AI.",
        kind: "network",
      }),
    )
    .mockResolvedValueOnce(processingRuns());
  renderPage();

  await user.click(
    await screen.findByRole("button", { name: "Próxima página" }),
  );
  expect(await screen.findByText("O backend está indisponível")).toBeInTheDocument();
  expect(screen.queryByText("run-2")).not.toBeInTheDocument();
  expect(
    screen.getByRole("button", { name: "Página anterior" }),
  ).toBeEnabled();

  await user.click(screen.getByRole("button", { name: "Tentar novamente" }));
  expect(await screen.findByText("run-2")).toBeInTheDocument();
  expect(getProcessingRunsMock).toHaveBeenLastCalledWith(
    { cursor: "failed-page" },
    expect.any(AbortSignal),
  );
});

test("a stale response cannot replace a newer refetch", async () => {
  let resolveFirst: (value: ReturnType<typeof processingRuns>) => void =
    () => undefined;
  let resolveSecond: (value: ReturnType<typeof processingRuns>) => void =
    () => undefined;
  getProcessingRunsMock
    .mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          resolveFirst = resolve;
        }),
    )
    .mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          resolveSecond = resolve;
        }),
    );
  const { result } = renderHook(() => useProcessingRuns());

  act(() => result.current.refetch());
  resolveSecond(
    processingRuns({
      items: [{ ...processingRuns().items[0], processing_run_id: "new-run" }],
    }),
  );
  await waitFor(() =>
    expect(result.current.data?.items[0].processing_run_id).toBe("new-run"),
  );
  resolveFirst(
    processingRuns({
      items: [{ ...processingRuns().items[0], processing_run_id: "old-run" }],
    }),
  );
  await waitFor(() =>
    expect(result.current.data?.items[0].processing_run_id).toBe("new-run"),
  );
});

test("aborts the active request when unmounted", () => {
  let receivedSignal: AbortSignal | undefined;
  getProcessingRunsMock.mockImplementation((_query, signal) => {
    receivedSignal = signal;
    return new Promise(() => undefined);
  });
  const view = renderPage();
  expect(receivedSignal?.aborted).toBe(false);
  view.unmount();
  expect(receivedSignal?.aborted).toBe(true);
});
