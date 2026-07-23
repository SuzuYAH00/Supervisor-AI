import {
  getFinancialSummary,
  parseFinancialSummary,
} from "../src/features/financial-summary/api/get-financial-summary";
import { financialSummary } from "./fixtures";

test("uses only provided filters and returns the validated contract", async () => {
  const payload = financialSummary();
  const fetchMock = vi
    .fn<typeof fetch>()
    .mockResolvedValue(new Response(JSON.stringify(payload), { status: 200 }));
  vi.stubGlobal("fetch", fetchMock);

  await expect(
    getFinancialSummary({
      collaboratorId: "employee 1",
      endDate: "2026-07-31",
    }),
  ).resolves.toEqual(payload);
  expect(fetchMock).toHaveBeenCalledWith(
    "/api/financial/summary?collaborator_id=employee+1&end_date=2026-07-31",
    expect.objectContaining({ headers: { Accept: "application/json" } }),
  );
});

test("parser preserves decimal strings and every public contract field", () => {
  const parsed = parseFinancialSummary(financialSummary());

  expect(parsed.totals_by_currency[0]?.amount).toBe("219.80");
  expect(
    parsed.collaborators[0]?.totals_by_currency[0]?.share_percentage,
  ).toBe("12.50");
  expect(parsed.collaborators[0]?.totals_by_currency[0]?.rank).toBe(9);
});

test("rejects an incompatible successful contract", async () => {
  vi.stubGlobal(
    "fetch",
    vi
      .fn<typeof fetch>()
      .mockResolvedValue(new Response('{"collaborators":[]}', { status: 200 })),
  );
  await expect(getFinancialSummary()).rejects.toMatchObject({
    code: "invalid_response",
  });
});

test("rejects numeric money instead of coercing it", () => {
  const invalid = {
    ...financialSummary(),
    totals_by_currency: [{ currency: "BRL", amount: 10 }],
  };
  expect(() => parseFinancialSummary(invalid)).toThrow(TypeError);
});
