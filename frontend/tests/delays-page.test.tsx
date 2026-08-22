import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";

import { createDelayReview, getOperationalDelays } from "../src/features/delays/api/delays";
import { DelaysPage } from "../src/features/delays/pages/DelaysPage";
import { ApiError } from "../src/lib/http/api-error";

vi.mock("../src/features/delays/api/delays", () => ({
  getOperationalDelays: vi.fn(),
  createDelayReview: vi.fn(),
}));

const getDelays = vi.mocked(getOperationalDelays);
const createReview = vi.mocked(createDelayReview);
const page = (entry = "/delays") => render(<MemoryRouter initialEntries={[entry]}><DelaysPage /></MemoryRouter>);

function result(status: "pending_review" | "corrected" = "pending_review") {
  return {
    competence_month: "2026-08", detected_count: 1,
    pending_count: status === "pending_review" ? 1 : 0,
    valid_count: 0, corrected_count: status === "corrected" ? 1 : 0,
    items: [{
      delay_occurrence_id: "delay-1", collaborator_id: "operator-1",
      display_name: "operator-1", occurrence_date: "2026-08-05",
      occurrence_type: "pause_duration" as const, review_status: status,
      counts_for_rv: status !== "corrected", observed_seconds: 342,
      applied_limit_seconds: 300,
      source_fact: { queue: "Support", started_at: "2026-08-05T12:00:00Z", ended_at: "2026-08-05T12:05:42Z", duration_seconds: 342, pause_type: "Banheiro" },
      schedule: null, review: null,
      possible_employee_occurrence_reports: [
        { id: "report-1", external_reference: "forms-1", external_collaborator_identity: "Operator", submitted_at: "2026-08-05T13:00:00Z", occurrence_date: "2026-08-05", reason_text: "Computador não iniciou corretamente" },
        { id: "report-2", external_reference: "forms-2", external_collaborator_identity: "Operator", submitted_at: "2026-08-05T14:00:00Z", occurrence_date: "2026-08-05", reason_text: "Outra declaração do mesmo dia" },
      ],
    }],
  };
}

test("shows evidence without choosing it and records a corrected review", async () => {
  const user = userEvent.setup();
  getDelays.mockResolvedValueOnce(result()).mockResolvedValueOnce(result("corrected"));
  createReview.mockResolvedValue({ id: "review-1", decision: "corrected", decided_at: "2026-08-06T12:00:00Z", decided_by: "mvp-supervisor", employee_occurrence_report_id: null, note: null });
  page();
  expect(await screen.findByText("Pendente — continua contando")).toBeInTheDocument();
  expect(screen.getByText("Possíveis ocorrências (2)")).toBeInTheDocument();
  await user.click(screen.getByText("Possíveis ocorrências (2)"));
  expect(screen.getByText("Computador não iniciou corretamente")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Revisar atraso" }));
  expect(screen.getByLabelText("Ocorrência usada como evidência")).toHaveValue("");
  await user.selectOptions(screen.getByLabelText("Decisão"), "corrected");
  await user.click(screen.getByRole("button", { name: "Salvar revisão" }));
  await waitFor(() => expect(createReview).toHaveBeenCalledWith("delay-1", { decision: "corrected" }));
  expect(await screen.findByText("Corrigido")).toBeInTheDocument();
});

test("forwards filters and presents HTTP errors", async () => {
  const user = userEvent.setup();
  getDelays.mockResolvedValueOnce(result()).mockRejectedValueOnce(new ApiError({ code: "network_error", message: "Falha operacional", kind: "network" }));
  page();
  await screen.findByText("Pendente — continua contando");
  await user.selectOptions(screen.getByLabelText("Tipo"), "entry");
  expect(await screen.findByRole("alert")).toHaveTextContent("Falha operacional");
  expect(getDelays).toHaveBeenLastCalledWith(expect.objectContaining({ delayType: "entry" }), expect.any(AbortSignal));
});

test("records the explicit decision to keep a delay", async () => {
  const user = userEvent.setup();
  getDelays.mockResolvedValue(result());
  createReview.mockResolvedValue({ id: "review-valid", decision: "valid", decided_at: "2026-08-06T12:00:00Z", decided_by: "mvp-supervisor", employee_occurrence_report_id: null, note: null });
  page();
  await screen.findByText("Pendente — continua contando");
  await user.click(screen.getByRole("button", { name: "Revisar atraso" }));
  await user.click(screen.getByRole("button", { name: "Salvar revisão" }));
  await waitFor(() => expect(createReview).toHaveBeenCalledWith("delay-1", { decision: "valid" }));
});

test("initializes competence and collaborator from navigation parameters", async () => {
  getDelays.mockResolvedValue(result());
  page("/delays?competence_month=2026-07&collaborator_id=operator-1");
  await screen.findByText("Pendente — continua contando");
  expect(getDelays).toHaveBeenCalledWith(
    expect.objectContaining({ competenceMonth: "2026-07", collaboratorId: "operator-1" }),
    expect.any(AbortSignal),
  );
});
