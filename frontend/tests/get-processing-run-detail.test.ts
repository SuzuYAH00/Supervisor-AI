import {
  getProcessingRunDetail,
  parseProcessingRunDetail,
} from "../src/features/processing-runs/api/get-processing-run-detail";
import { processingRunDetail } from "./fixtures";

test("parser preserves the complete allowlisted detail", () => {
  const payload = processingRunDetail();
  expect(parseProcessingRunDetail(payload)).toEqual(payload);
});

test("parser accepts an empty phase list", () => {
  const payload = processingRunDetail({ phases: [] });
  expect(parseProcessingRunDetail(payload)).toEqual(payload);
});

test.each([
  { payload: {}, description: "missing root objects" },
  {
    payload: {
      ...processingRunDetail(),
      processing_run: {
        ...processingRunDetail().processing_run,
        completed_at: null,
      },
    },
    description: "null required timestamp",
  },
  {
    payload: {
      ...processingRunDetail(),
      commercial_event: {
        ...processingRunDetail().commercial_event,
        source: 10,
      },
    },
    description: "invalid nested event",
  },
  {
    payload: {
      ...processingRunDetail(),
      phases: [
        {
          phase: "contract_facts",
          status: "completed",
          can_continue: "true",
        },
      ],
    },
    description: "invalid phase item",
  },
  {
    payload: { ...processingRunDetail(), phases: null },
    description: "invalid phase list",
  },
])("parser rejects $description", ({ payload }) => {
  expect(() => parseProcessingRunDetail(payload)).toThrow(TypeError);
});

test("client encodes the ID and forwards AbortSignal", async () => {
  const payload = processingRunDetail();
  const controller = new AbortController();
  const fetchMock = vi
    .fn<typeof fetch>()
    .mockResolvedValue(new Response(JSON.stringify(payload), { status: 200 }));
  vi.stubGlobal("fetch", fetchMock);

  await expect(
    getProcessingRunDetail("run /with+characters", controller.signal),
  ).resolves.toEqual(payload);
  expect(fetchMock).toHaveBeenCalledWith(
    "/api/processing-runs/run%20%2Fwith%2Bcharacters",
    expect.objectContaining({ signal: controller.signal }),
  );
});

test("client rejects an invalid HTTP 200 response", async () => {
  vi.stubGlobal(
    "fetch",
    vi
      .fn<typeof fetch>()
      .mockResolvedValue(new Response('{"phases":[]}', { status: 200 })),
  );

  await expect(getProcessingRunDetail("run-1")).rejects.toMatchObject({
    code: "invalid_response",
  });
});
