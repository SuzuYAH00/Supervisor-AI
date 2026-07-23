import {
  getCommercialEventDetail,
  parseCommercialEventDetail,
} from "../src/features/commercial-events/api/get-commercial-event-detail";
import { commercialEventDetail } from "./fixtures";

test("parses the related event, ledger and processing runs", () => {
  const payload = commercialEventDetail();
  expect(parseCommercialEventDetail(payload)).toEqual(payload);
});

test("accepts empty related collections", () => {
  const payload = commercialEventDetail({
    ledger_entries: [],
    processing_runs: [],
  });
  expect(parseCommercialEventDetail(payload)).toEqual(payload);
});

test("encodes the event ID and validates the response", async () => {
  const payload = commercialEventDetail();
  const fetchMock = vi
    .fn<typeof fetch>()
    .mockResolvedValue(new Response(JSON.stringify(payload), { status: 200 }));
  vi.stubGlobal("fetch", fetchMock);

  await expect(getCommercialEventDetail("event /1")).resolves.toEqual(payload);
  expect(fetchMock).toHaveBeenCalledWith(
    "/api/commercial-events/event%20%2F1",
    expect.any(Object),
  );
});

test("rejects an incompatible successful response", async () => {
  vi.stubGlobal(
    "fetch",
    vi
      .fn<typeof fetch>()
      .mockResolvedValue(new Response('{"processing_runs":[]}', { status: 200 })),
  );
  await expect(getCommercialEventDetail("event-1")).rejects.toMatchObject({
    code: "invalid_response",
  });
});
