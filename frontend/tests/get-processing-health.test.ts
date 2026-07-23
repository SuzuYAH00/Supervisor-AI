import { getProcessingHealth } from "../src/features/processing-health/api/get-processing-health";
import { processingHealth } from "./fixtures";

test("uses only provided filters and returns the explicit contract", async () => {
  const payload = processingHealth();
  const fetchMock = vi
    .fn<typeof fetch>()
    .mockResolvedValue(new Response(JSON.stringify(payload), { status: 200 }));
  vi.stubGlobal("fetch", fetchMock);

  await expect(
    getProcessingHealth({
      source: "csv example",
      startDate: "2026-07-01",
    }),
  ).resolves.toEqual(payload);
  expect(fetchMock).toHaveBeenCalledWith(
    "/api/processing/health?start_date=2026-07-01&source=csv+example",
    expect.objectContaining({
      headers: { Accept: "application/json" },
    }),
  );
});

test("rejects an incompatible successful contract", async () => {
  vi.stubGlobal(
    "fetch",
    vi
      .fn<typeof fetch>()
      .mockResolvedValue(new Response('{"processing_runs":{}}', { status: 200 })),
  );
  await expect(getProcessingHealth()).rejects.toMatchObject({
    code: "invalid_response",
  });
});
