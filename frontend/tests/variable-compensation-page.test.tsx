import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";

import { getVariableCompensation } from "../src/features/variable-compensation/api/variable-compensation";
import { VariableCompensationPage } from "../src/features/variable-compensation/pages/VariableCompensationPage";
import type { VariableCompensationResult } from "../src/features/variable-compensation/types/variable-compensation";
import { ApiError } from "../src/lib/http/api-error";

vi.mock("../src/features/variable-compensation/api/variable-compensation", () => ({ getVariableCompensation: vi.fn() }));
const getClosure = vi.mocked(getVariableCompensation);
const page = () => render(<MemoryRouter><VariableCompensationPage /></MemoryRouter>);

function result(status: "calculated" | "incomplete" = "calculated", total = "975.00"): VariableCompensationResult {
  const issues = status === "incomplete" ? [{ code: "recurrence_coverage_incomplete", component: "recurrence" as const, scope: "competence" as const, collaborator_id: null, affected_collaborator_ids: ["operator-1"], competence_month: "2026-08", message: "A janela de observação da Reincidência ainda não possui cobertura completa.", severity: "blocking" as const, blocking: true, action_type: "review_recurrence_import", action_target: null, metadata: {} }] : [];
  return { competence_month: "2026-08", collaborator_count: 1, calculated_count: status === "calculated" ? 1 : 0, incomplete_count: status === "incomplete" ? 1 : 0, projected_total: status === "calculated" ? total : null, issue_summary: { total_count: issues.length, blocking_count: issues.length, by_component: status === "incomplete" ? { recurrence: 1 } : {} }, issues, items: [{ collaborator_id: "operator-1", display_name: "operator-1", status, pending_reasons: issues.map((issue) => issue.code), pending_issues: issues, csat: { status: "eligible", reference_month: "2026-08", eligible: true, tier: "gold", amount: "800.00", individual_value: "9.60", team_average: "9.20", modality: "chat", response_rate: "0.50", minimum_response_rate: "0.40" }, recurrence: { status: "eligible", reference_month: "2026-07", eligible: true, tier: "silver", amount: "200.00", individual_value: "0.08", team_average: "0.14", team_average_cap_passed: true }, delays: { count: 2, amount: "-25.00" }, absences: { count: 0, amount: "0.00" }, positive_amount: status === "calculated" ? "1000.00" : null, deductions_amount: status === "calculated" ? "-25.00" : null, total_amount: status === "calculated" ? total : null }] };
}

test("renders calculated components and totals", async () => {
  getClosure.mockResolvedValue(result()); page();
  expect(await screen.findByText("Calculado")).toBeInTheDocument();
  expect(screen.getByText((_, element) => element?.tagName === "P" && element.textContent === "Ouro · R$ 800,00")).toBeInTheDocument();
  expect(screen.getByText((_, element) => element?.tagName === "STRONG" && element.textContent === "Total R$ 975,00")).toBeInTheDocument();
});

test("keeps incomplete totals pending and forwards filters", async () => {
  const user = userEvent.setup(); getClosure.mockResolvedValue(result("incomplete")); page();
  expect(await screen.findByText("Fechamento pendente")).toBeInTheDocument();
  expect(screen.getAllByText("A janela de observação da Reincidência ainda não possui cobertura completa.").length).toBeGreaterThan(0);
  expect(screen.queryByText("recurrence_coverage_incomplete")).not.toBeInTheDocument();
  await user.selectOptions(screen.getByLabelText("Situação"), "incomplete");
  expect(getClosure).toHaveBeenLastCalledWith(expect.objectContaining({ status: "incomplete" }), expect.any(AbortSignal));
});

test("renders negative total, loading, empty and error states", async () => {
  getClosure.mockResolvedValueOnce(result("calculated", "-25.00")); const first = page();
  expect(await screen.findByText((_, element) => element?.tagName === "STRONG" && element.textContent === "Total -R$ 25,00")).toBeInTheDocument(); first.unmount();
  getClosure.mockResolvedValueOnce({ ...result(), collaborator_count: 0, calculated_count: 0, items: [], projected_total: "0.00", issue_summary: { total_count: 0, blocking_count: 0, by_component: {} }, issues: [] }); const empty = page();
  expect(screen.getByRole("status")).toHaveTextContent("Carregando"); expect(await screen.findByText("Nenhum colaborador encontrado para os filtros informados.")).toBeInTheDocument(); empty.unmount();
  getClosure.mockRejectedValueOnce(new ApiError({ code: "network", message: "Falha ao consultar", kind: "network" })); page();
  expect(await screen.findByRole("alert")).toHaveTextContent("Falha ao consultar");
});
