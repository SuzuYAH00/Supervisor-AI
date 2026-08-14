import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";

import { importCsv } from "../src/features/csv-import/api/import-csv";
import { CsvImportPage } from "../src/features/csv-import/pages/CsvImportPage";
import { ApiError } from "../src/lib/http/api-error";
import { csvImportResult } from "./csv-import-fixture";

vi.mock("../src/features/csv-import/api/import-csv", () => ({ importCsv: vi.fn() }));
const importCsvMock = vi.mocked(importCsv);
const renderPage = () => render(<MemoryRouter><CsvImportPage /></MemoryRouter>);

test("validates selection, extension, and empty files locally", () => {
  renderPage();
  const input = screen.getByLabelText("Selecione um arquivo CSV");
  expect(screen.getByRole("button", { name: "Importar CSV" })).toBeDisabled();
  fireEvent.change(input, { target: { files: [new File(["x"], "events.txt")] } });
  expect(screen.getByRole("alert")).toHaveTextContent("extensão .csv");
  fireEvent.change(input, {
    target: { files: [new File([], "empty.csv", { type: "text/csv" })] },
  });
  expect(screen.getByRole("alert")).toHaveTextContent("não pode estar vazio");
  expect(importCsvMock).not.toHaveBeenCalled();
});

test("submits the selected file, blocks duplicates, and shows the contract", async () => {
  const user = userEvent.setup();
  let resolveRequest: (value: typeof csvImportResult) => void = () => undefined;
  importCsvMock.mockReturnValue(new Promise((resolve) => { resolveRequest = resolve; }));
  renderPage();
  const file = new File(["header\nvalue"], "events.csv", { type: "text/csv" });
  await user.upload(screen.getByLabelText("Selecione um arquivo CSV"), file);
  const button = screen.getByRole("button", { name: "Importar CSV" });
  await user.click(button);
  expect(button).toBeDisabled();
  expect(importCsvMock).toHaveBeenCalledWith(file, expect.any(AbortSignal));
  resolveRequest(csvImportResult);
  expect(await screen.findByText("Resultado da importação")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "run/1" })).toHaveAttribute(
    "href", "/processing-runs/run%2F1",
  );
  expect(screen.getByText("Documentos processados").nextSibling).toHaveTextContent("1");
});

test("retries an API error with the same file", async () => {
  const user = userEvent.setup();
  importCsvMock.mockRejectedValueOnce(new ApiError({
    status: 400, code: "csv_structure_error",
    message: "CSV structure is invalid", kind: "api",
  })).mockResolvedValueOnce(csvImportResult);
  renderPage();
  const file = new File(["x"], "events.csv", { type: "text/csv" });
  await user.upload(screen.getByLabelText("Selecione um arquivo CSV"), file);
  await user.click(screen.getByRole("button", { name: "Importar CSV" }));
  expect(await screen.findByText("CSV structure is invalid")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Tentar novamente" }));
  expect(await screen.findByText("Resultado da importação")).toBeInTheDocument();
  expect(importCsvMock).toHaveBeenNthCalledWith(2, file, expect.any(AbortSignal));
});

test("a new selection clears a previous local error", () => {
  renderPage();
  const input = screen.getByLabelText("Selecione um arquivo CSV");
  fireEvent.change(input, { target: { files: [new File(["x"], "invalid.txt")] } });
  expect(screen.getByRole("alert")).toBeInTheDocument();
  fireEvent.change(input, {
    target: { files: [new File(["x"], "valid.csv", { type: "text/csv" })] },
  });
  expect(screen.queryByRole("alert")).not.toBeInTheDocument();
});

test("unmount aborts the active upload", async () => {
  const user = userEvent.setup();
  let signal: AbortSignal | undefined;
  importCsvMock.mockImplementation((_file, receivedSignal) => {
    signal = receivedSignal;
    return new Promise(() => undefined);
  });
  const view = renderPage();
  await user.upload(screen.getByLabelText("Selecione um arquivo CSV"), new File(["x"], "events.csv"));
  await user.click(screen.getByRole("button", { name: "Importar CSV" }));
  await waitFor(() => expect(signal?.aborted).toBe(false));
  view.unmount();
  expect(signal?.aborted).toBe(true);
});
