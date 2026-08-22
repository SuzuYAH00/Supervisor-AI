import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";

import { getWorkSchedules, createWorkScheduleOverride } from "../src/features/work-schedules/api/work-schedules";
import { WorkSchedulesPage } from "../src/features/work-schedules/pages/WorkSchedulesPage";

vi.mock("../src/features/work-schedules/api/work-schedules", () => ({
  getWorkSchedules: vi.fn(),
  createWorkScheduleOverride: vi.fn(),
}));

const getSchedules = vi.mocked(getWorkSchedules);
const createOverride = vi.mocked(createWorkScheduleOverride);

test("highlights pending schedules and creates a manual override", async () => {
  const user = userEvent.setup();
  getSchedules.mockResolvedValue({
    competence_month: "2026-08", total_count: 1, pending_count: 1,
    items: [{
      collaborator_id: "operator-1", display_name: "operator-1",
      work_date: "2026-08-20", planned_start: null, planned_end: null,
      resolution_status: "unresolved", effective_origin: "unresolved",
      source: "attendance_sheet", source_reference: "august:D20",
      source_sheet: "AGOSTO", source_cell: "D20",
      unresolved_reason: "explicit_schedule_not_found", has_override: false,
      override: null,
    }],
  });
  createOverride.mockResolvedValue({
    id: "override-1", collaborator_id: "operator-1", work_date: "2026-08-20",
    planned_start: "16:00:00", planned_end: "22:00:00",
    reason: "troca de expediente", created_by: "mvp-supervisor",
    created_at: "2026-08-19T12:00:00+00:00",
  });

  render(<MemoryRouter initialEntries={["/work-schedules?competence_month=2026-08&collaborator_id=operator-1&resolution_status=pending"]}><WorkSchedulesPage /></MemoryRouter>);
  expect(await screen.findByText("Jornada pendente")).toBeInTheDocument();
  expect(screen.getByText(/Jornadas pendentes:/)).toHaveTextContent("1");
  expect(getSchedules).toHaveBeenCalledWith(expect.objectContaining({ competenceMonth: "2026-08", collaboratorId: "operator-1", resolutionStatus: "pending" }), expect.any(AbortSignal));
  await user.click(screen.getByRole("button", { name: "Definir jornada manualmente" }));
  await user.type(screen.getByLabelText("Horário inicial"), "16:00");
  await user.type(screen.getByLabelText("Horário final"), "22:00");
  await user.type(screen.getByLabelText("Motivo"), "troca de expediente");
  await user.click(screen.getByRole("button", { name: "Salvar override" }));
  await waitFor(() => expect(createOverride).toHaveBeenCalledWith({
    collaborator_id: "operator-1", work_date: "2026-08-20",
    planned_start: "16:00", planned_end: "22:00",
    reason: "troca de expediente",
  }));
});
