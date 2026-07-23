import {
  getFinancialTimeline,
  parseFinancialTimeline,
} from "../src/features/financial-timeline/api/get-financial-timeline";
import { financialTimeline } from "./fixtures";

test("parser preserves the complete public timeline contract", () => {
  const payload = financialTimeline({
    filters: {
      start_date: "2026-07-01",
      end_date: null,
      entry_type: "credit",
      currency: null,
    },
    page: { limit: 1, next_cursor: "opaque-cursor", has_more: true },
  });
  const parsed = parseFinancialTimeline(payload);

  expect(parsed).toEqual(payload);
  expect(parsed.items[0]?.amount).toBe("99.90");
  expect(parsed.items[0]?.invoice_id).toBeNull();
  expect(parsed.items[0]?.posted_at).toBe("2026-07-22T12:05:00Z");
});

test("parser accepts an empty timeline and a null cursor", () => {
  const payload = financialTimeline({ items: [] });
  expect(parseFinancialTimeline(payload)).toEqual(payload);
});

test.each([
  { page: { limit: 1, next_cursor: null, has_more: true } },
  { page: { limit: 1, next_cursor: "unexpected", has_more: false } },
])("parser rejects inconsistent pagination: $page", ({ page }) => {
  expect(() => parseFinancialTimeline(financialTimeline({ page }))).toThrow(
    "Invalid pagination: has_more and next_cursor are inconsistent",
  );
});

test.each([
  {},
  { ...financialTimeline(), collaborator_id: 123 },
  {
    ...financialTimeline(),
    items: [{ ...financialTimeline().items[0], amount: 99.9 }],
  },
  {
    ...financialTimeline(),
    items: [{ ...financialTimeline().items[0], source_reference_ids: null }],
  },
])("parser rejects an incompatible contract", (payload) => {
  expect(() => parseFinancialTimeline(payload)).toThrow(TypeError);
});

test("client encodes collaborator and every supported filter", async () => {
  const payload = financialTimeline();
  const controller = new AbortController();
  const fetchMock = vi
    .fn<typeof fetch>()
    .mockResolvedValue(new Response(JSON.stringify(payload), { status: 200 }));
  vi.stubGlobal("fetch", fetchMock);

  await expect(
    getFinancialTimeline(
      "Employee/A B",
      {
        startDate: "2026-07-01",
        endDate: "2026-07-31",
        entryType: "credit",
        currency: "BRL",
        limit: 1,
        cursor: "opaque+/cursor==",
      },
      controller.signal,
    ),
  ).resolves.toEqual(payload);
  expect(fetchMock).toHaveBeenCalledWith(
    "/api/collaborators/Employee%2FA%20B/financial-timeline?start_date=2026-07-01&end_date=2026-07-31&entry_type=credit&currency=BRL&limit=1&cursor=opaque%2B%2Fcursor%3D%3D",
    expect.objectContaining({ signal: controller.signal }),
  );
});

test("client omits undefined parameters", async () => {
  vi.stubGlobal(
    "fetch",
    vi
      .fn<typeof fetch>()
      .mockResolvedValue(
        new Response(JSON.stringify(financialTimeline()), { status: 200 }),
      ),
  );
  await getFinancialTimeline("Employee-A");
  expect(fetch).toHaveBeenCalledWith(
    "/api/collaborators/Employee-A/financial-timeline",
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
  await expect(getFinancialTimeline("Employee-A")).rejects.toMatchObject({
    code: "invalid_response",
  });
});
