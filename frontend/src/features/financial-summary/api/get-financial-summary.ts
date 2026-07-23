import { apiRequest } from "../../../lib/http/api-client";
import {
  jsonList,
  jsonObject,
  nonNegativeInteger,
  nullableText,
  text,
} from "../../../lib/http/json-contract";
import type {
  CollaboratorCurrencySummary,
  CollaboratorFinancialSummary,
  CurrencyTotal,
  FinancialSummary,
  FinancialSummaryQuery,
} from "../types/financial-summary";

function currencyTotal(value: unknown): CurrencyTotal {
  const item = jsonObject(value, "totals_by_currency");
  return {
    currency: text(item.currency, "currency"),
    amount: text(item.amount, "amount"),
  };
}

function collaboratorCurrencySummary(
  value: unknown,
): CollaboratorCurrencySummary {
  const item = jsonObject(value, "collaborator totals_by_currency");
  return {
    currency: text(item.currency, "currency"),
    amount: text(item.amount, "amount"),
    credit_count: nonNegativeInteger(item.credit_count, "credit_count"),
    rank: nonNegativeInteger(item.rank, "rank"),
    share_percentage: text(item.share_percentage, "share_percentage"),
  };
}

function collaboratorSummary(value: unknown): CollaboratorFinancialSummary {
  const item = jsonObject(value, "collaborators");
  return {
    collaborator_id: text(item.collaborator_id, "collaborator_id"),
    credit_count: nonNegativeInteger(item.credit_count, "credit_count"),
    totals_by_currency: jsonList(
      item.totals_by_currency,
      collaboratorCurrencySummary,
      "totals_by_currency",
    ),
  };
}

export function parseFinancialSummary(value: unknown): FinancialSummary {
  const root = jsonObject(value, "root");
  const filters = jsonObject(root.filters, "filters");
  return {
    filters: {
      collaborator_id: nullableText(
        filters.collaborator_id,
        "collaborator_id",
      ),
      start_date: nullableText(filters.start_date, "start_date"),
      end_date: nullableText(filters.end_date, "end_date"),
    },
    collaborator_count: nonNegativeInteger(
      root.collaborator_count,
      "collaborator_count",
    ),
    credit_count: nonNegativeInteger(root.credit_count, "credit_count"),
    totals_by_currency: jsonList(
      root.totals_by_currency,
      currencyTotal,
      "totals_by_currency",
    ),
    collaborators: jsonList(
      root.collaborators,
      collaboratorSummary,
      "collaborators",
    ),
  };
}

export function getFinancialSummary(
  filters: FinancialSummaryQuery = {},
  signal?: AbortSignal,
): Promise<FinancialSummary> {
  const parameters = new URLSearchParams();
  if (filters.collaboratorId !== undefined) {
    parameters.set("collaborator_id", filters.collaboratorId);
  }
  if (filters.startDate !== undefined) {
    parameters.set("start_date", filters.startDate);
  }
  if (filters.endDate !== undefined) {
    parameters.set("end_date", filters.endDate);
  }
  const query = parameters.toString();
  const path =
    query === "" ? "/financial/summary" : `/financial/summary?${query}`;
  return apiRequest(path, { signal, parse: parseFinancialSummary });
}
