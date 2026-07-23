import {
  getProcessingRuns,
} from "../src/features/processing-runs/api/get-processing-runs";
import { parseProcessingRuns } from "../src/features/processing-runs/types/processing-runs";
import { processingRuns } from "./fixtures";

test("parser accepts the real response and preserves factual fields", () => {
  const payload = processingRuns({ next_cursor: "opaque+/cursor==" });

  expect(parseProcessingRuns(payload)).toEqual(payload);
  expect(parseProcessingRuns(payload).items[0]).toMatchObject({
    final_status: "posted",
    started_at: "2026-07-23T14:00:00Z",
    completed_at: "2026-07-23T14:00:01Z",
  });
});

test("parser accepts an empty collection and null cursor", () => {
  const payload = processingRuns({ items: [], next_cursor: null });
  expect(parseProcessingRuns(payload)).toEqual(payload);
});

test.each([
  { payload: {}, description: "missing root fields" },
  {
    payload: { ...processingRuns(), next_cursor: 12 },
    description: "invalid cursor",
  },
  {
    payload: {
      ...processingRuns(),
      items: [{ ...processingRuns().items[0], final_status: null }],
    },
    description: "invalid item",
  },
  {
    payload: {
      ...processingRuns(),
      items: [{ ...processingRuns().items[0], started_at: 123 }],
    },
    description: "invalid timestamp",
  },
])("parser rejects $description", ({ payload }) => {
  expect(() => parseProcessingRuns(payload)).toThrow(TypeError);
});

test("client serializes all real filters and forwards AbortSignal", async () => {
  const payload = processingRuns();
  const controller = new AbortController();
  const fetchMock = vi
    .fn<typeof fetch>()
    .mockResolvedValue(new Response(JSON.stringify(payload), { status: 200 }));
  vi.stubGlobal("fetch", fetchMock);

  await expect(
    getProcessingRuns(
      {
        source: "csv example",
        externalReference: "external/1",
        finalStatus: "posted value",
        rulesEngineVersion: "rules+1",
        startDate: "2026-07-01",
        endDate: "2026-07-31",
        limit: 10,
        cursor: "opaque+/cursor==",
      },
      controller.signal,
    ),
  ).resolves.toEqual(payload);

  expect(fetchMock).toHaveBeenCalledWith(
    "/api/processing-runs?source=csv+example&external_reference=external%2F1&final_status=posted+value&rules_engine_version=rules%2B1&start_date=2026-07-01&end_date=2026-07-31&limit=10&cursor=opaque%2B%2Fcursor%3D%3D",
    expect.objectContaining({ signal: controller.signal }),
  );
});

test("client omits undefined query parameters", async () => {
  vi.stubGlobal(
    "fetch",
    vi
      .fn<typeof fetch>()
      .mockResolvedValue(
        new Response(JSON.stringify(processingRuns()), { status: 200 }),
      ),
  );

  await getProcessingRuns();
  expect(fetch).toHaveBeenCalledWith("/api/processing-runs", expect.any(Object));
});

test("client rejects an invalid successful response", async () => {
  vi.stubGlobal(
    "fetch",
    vi
      .fn<typeof fetch>()
      .mockResolvedValue(new Response('{"items":[]}', { status: 200 })),
  );

  await expect(getProcessingRuns()).rejects.toMatchObject({
    code: "invalid_response",
  });
});
