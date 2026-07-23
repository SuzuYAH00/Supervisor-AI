import {
  getCommercialEvents,
  parseCommercialEvents,
} from "../src/features/commercial-events/api/get-commercial-events";
import { commercialEvents } from "./fixtures";

test("parser accepts the complete response and preserves the opaque cursor", () => {
  const payload = commercialEvents({
    filters: {
      source: "csv-example",
      external_reference: null,
      start_date: null,
      end_date: "2026-07-31",
    },
    page: {
      limit: 1,
      next_cursor: "opaque+/cursor==",
      has_more: true,
    },
  });

  expect(parseCommercialEvents(payload)).toEqual(payload);
});

test("parser accepts an empty collection and null cursor", () => {
  const payload = commercialEvents({ items: [] });
  expect(parseCommercialEvents(payload)).toEqual(payload);
});

test("parser rejects has_more true without a next cursor", () => {
  const payload = commercialEvents({
    page: { limit: 50, next_cursor: null, has_more: true },
  });
  expect(() => parseCommercialEvents(payload)).toThrow(
    "Invalid pagination: has_more and next_cursor are inconsistent",
  );
});

test("parser rejects a next cursor when has_more is false", () => {
  const payload = commercialEvents({
    page: { limit: 50, next_cursor: "unexpected-cursor", has_more: false },
  });
  expect(() => parseCommercialEvents(payload)).toThrow(
    "Invalid pagination: has_more and next_cursor are inconsistent",
  );
});

test.each([
  { payload: {}, description: "missing root fields" },
  {
    payload: {
      ...commercialEvents(),
      page: { limit: 50, next_cursor: null, has_more: "false" },
    },
    description: "invalid boolean",
  },
  {
    payload: {
      ...commercialEvents(),
      items: [{ ...commercialEvents().items[0], occurred_at: null }],
    },
    description: "invalid event field",
  },
])("parser rejects $description", ({ payload }) => {
  expect(() => parseCommercialEvents(payload)).toThrow(TypeError);
});

test("client serializes supported filters and forwards AbortSignal", async () => {
  const payload = commercialEvents();
  const controller = new AbortController();
  const fetchMock = vi
    .fn<typeof fetch>()
    .mockResolvedValue(new Response(JSON.stringify(payload), { status: 200 }));
  vi.stubGlobal("fetch", fetchMock);

  await expect(
    getCommercialEvents(
      {
        source: "csv example",
        externalReference: "external/1",
        startDate: "2026-07-01",
        endDate: "2026-07-31",
        limit: 10,
        cursor: "opaque+/cursor==",
      },
      controller.signal,
    ),
  ).resolves.toEqual(payload);

  expect(fetchMock).toHaveBeenCalledWith(
    "/api/commercial-events?source=csv+example&external_reference=external%2F1&start_date=2026-07-01&end_date=2026-07-31&limit=10&cursor=opaque%2B%2Fcursor%3D%3D",
    expect.objectContaining({ signal: controller.signal }),
  );
});

test("client omits undefined query parameters", async () => {
  vi.stubGlobal(
    "fetch",
    vi
      .fn<typeof fetch>()
      .mockResolvedValue(
        new Response(JSON.stringify(commercialEvents()), { status: 200 }),
      ),
  );
  await getCommercialEvents();
  expect(fetch).toHaveBeenCalledWith(
    "/api/commercial-events",
    expect.any(Object),
  );
});

test("client rejects an invalid successful response", async () => {
  vi.stubGlobal(
    "fetch",
    vi
      .fn<typeof fetch>()
      .mockResolvedValue(new Response('{"items":[]}', { status: 200 })),
  );
  await expect(getCommercialEvents()).rejects.toMatchObject({
    code: "invalid_response",
  });
});
