import { importCsv, parseCsvImportResult } from "../src/features/csv-import/api/import-csv";
import { csvImportResult } from "./csv-import-fixture";

test("parser preserves the complete valid contract", () => {
  expect(parseCsvImportResult(csvImportResult)).toEqual(csvImportResult);
});

test("parser rejects an incompatible successful response", () => {
  expect(() => parseCsvImportResult({
    ...csvImportResult,
    processing: { ...csvImportResult.processing, total_documents: "1" },
  })).toThrow(TypeError);
});

test("client sends multipart without defining Content-Type", async () => {
  const file = new File(["header\nvalue"], "events.csv", { type: "text/csv" });
  const controller = new AbortController();
  const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(
    new Response(JSON.stringify(csvImportResult), { status: 200 }),
  );
  vi.stubGlobal("fetch", fetchMock);
  await expect(importCsv(file, controller.signal)).resolves.toEqual(csvImportResult);
  const [url, options] = fetchMock.mock.calls[0];
  expect(url).toBe("/api/imports/csv");
  expect(options?.method).toBe("POST");
  expect(options?.signal).toBe(controller.signal);
  expect(options?.body).toBeInstanceOf(FormData);
  expect((options?.body as FormData).get("file")).toBe(file);
  expect(new Headers(options?.headers).has("Content-Type")).toBe(false);
});
