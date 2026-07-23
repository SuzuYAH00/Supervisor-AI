import {
  act,
  render,
  renderHook,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";

import { getProcessingRunDetail } from "../src/features/processing-runs/api/get-processing-run-detail";
import { useProcessingRunDetail } from "../src/features/processing-runs/hooks/use-processing-run-detail";
import { ProcessingRunDetailPage } from "../src/features/processing-runs/pages/ProcessingRunDetailPage";
import { ApiError } from "../src/lib/http/api-error";
import { processingRunDetail } from "./fixtures";

vi.mock(
  "../src/features/processing-runs/api/get-processing-run-detail",
  () => ({ getProcessingRunDetail: vi.fn() }),
);

const getProcessingRunDetailMock = vi.mocked(getProcessingRunDetail);

function renderDetail(path = "/processing-runs/run-1") {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route
          path="/processing-runs/:processingRunId"
          element={<ProcessingRunDetailPage />}
        />
      </Routes>
    </MemoryRouter>,
  );
}

test("loads and projects every public detail field", async () => {
  let resolveRequest: (value: ReturnType<typeof processingRunDetail>) => void =
    () => undefined;
  getProcessingRunDetailMock.mockReturnValue(
    new Promise((resolve) => {
      resolveRequest = resolve;
    }),
  );
  renderDetail();
  expect(
    screen.getByText("Carregando detalhes da execução"),
  ).toBeInTheDocument();

  resolveRequest(processingRunDetail());
  expect(await screen.findByText("Execução persistida")).toBeInTheDocument();
  expect(screen.getAllByText("run-1").length).toBeGreaterThan(0);
  expect(screen.getAllByText("event-1").length).toBeGreaterThan(0);
  expect(screen.getByText("posted")).toBeInTheDocument();
  expect(screen.getByText("rules-1")).toBeInTheDocument();
  expect(screen.getByText("external-1")).toBeInTheDocument();
  expect(screen.getByText("csv-example")).toBeInTheDocument();
  const phaseRow = screen.getByRole("row", {
    name: "payment_validation validated false",
  });
  expect(within(phaseRow).getByText("validated")).toBeInTheDocument();
  expect(screen.queryByText(/duração/i)).not.toBeInTheDocument();
  expect(screen.queryByText(/percentual/i)).not.toBeInTheDocument();
});

test("renders an empty phase collection as a successful detail", async () => {
  getProcessingRunDetailMock.mockResolvedValue(
    processingRunDetail({ phases: [] }),
  );
  renderDetail();
  expect(
    await screen.findByText("Nenhuma fase pública foi persistida."),
  ).toBeInTheDocument();
});

test("uses the confirmed public 404 code for the not-found state and retries", async () => {
  const user = userEvent.setup();
  getProcessingRunDetailMock
    .mockRejectedValueOnce(
      new ApiError({
        status: 404,
        code: "processing_run_not_found",
        message: "Processing run was not found",
        kind: "api",
      }),
    )
    .mockResolvedValueOnce(processingRunDetail());
  renderDetail("/processing-runs/missing");

  expect(await screen.findByText("Execução não encontrada")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Tentar novamente" }));
  expect(await screen.findByText("Execução persistida")).toBeInTheDocument();
  expect(getProcessingRunDetailMock).toHaveBeenLastCalledWith(
    "missing",
    expect.any(AbortSignal),
  );
});

test("uses the generic error state when the public not-found code is absent", async () => {
  getProcessingRunDetailMock.mockRejectedValue(
    new ApiError({
      status: 404,
      code: "unexpected_api_error",
      message: "O Supervisor AI não pôde concluir a solicitação.",
      kind: "api",
    }),
  );
  renderDetail();
  expect(
    await screen.findByText("A consulta não pôde ser concluída"),
  ).toBeInTheDocument();
  expect(screen.queryByText("Execução não encontrada")).not.toBeInTheDocument();
});

test("does not request an invalid decoded route ID", () => {
  renderDetail("/processing-runs/%20%20");
  expect(screen.getByText("Rota de execução inválida")).toBeInTheDocument();
  expect(getProcessingRunDetailMock).not.toHaveBeenCalled();
});

test("a stale response cannot replace a detail for a newer ID", async () => {
  let resolveFirst: (value: ReturnType<typeof processingRunDetail>) => void =
    () => undefined;
  let resolveSecond: (value: ReturnType<typeof processingRunDetail>) => void =
    () => undefined;
  getProcessingRunDetailMock
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
  const { result, rerender } = renderHook(
    ({ runId }: { runId: string }) => useProcessingRunDetail(runId),
    { initialProps: { runId: "run-a" } },
  );

  rerender({ runId: "run-b" });
  act(() => {
    resolveSecond(
      processingRunDetail({
        processing_run: {
          ...processingRunDetail().processing_run,
          processing_run_id: "run-b",
        },
      }),
    );
  });
  await waitFor(() =>
    expect(result.current.data?.processing_run.processing_run_id).toBe("run-b"),
  );
  act(() => {
    resolveFirst(
      processingRunDetail({
        processing_run: {
          ...processingRunDetail().processing_run,
          processing_run_id: "run-a",
        },
      }),
    );
  });
  await waitFor(() =>
    expect(result.current.data?.processing_run.processing_run_id).toBe("run-b"),
  );
});

test("aborts the active detail request when unmounted", () => {
  let receivedSignal: AbortSignal | undefined;
  getProcessingRunDetailMock.mockImplementation((_id, signal) => {
    receivedSignal = signal;
    return new Promise(() => undefined);
  });
  const view = renderDetail();
  expect(receivedSignal?.aborted).toBe(false);
  view.unmount();
  expect(receivedSignal?.aborted).toBe(true);
});
