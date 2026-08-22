import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { OperationalImportsPage } from "../src/features/operational-imports/pages/OperationalImportsPage";
import { getOperationalImportCatalog, uploadOperationalImport } from "../src/features/operational-imports/api/operational-imports";
import { ApiError } from "../src/lib/http/api-error";

vi.mock("../src/features/operational-imports/api/operational-imports", () => ({ getOperationalImportCatalog: vi.fn(), uploadOperationalImport: vi.fn() }));
const getCatalog = vi.mocked(getOperationalImportCatalog);
const upload = vi.mocked(uploadOperationalImport);
const catalog = { history_available: false, items: [
  { type: "workforce_schedule", label: "Escala", source: "attendance_sheet", status: "ready" as const, requires_competence: true, accepted_extensions: [".xlsx"], not_ready_reason: null },
  { type: "recurrence_mk", label: "Reincidência / MK", source: "mk", status: "not_ready" as const, requires_competence: true, accepted_extensions: [".xlsx"], not_ready_reason: "Parser indisponível." },
] };

beforeEach(() => { getCatalog.mockResolvedValue(catalog); });

test("initializes URL, uploads and presents structured result", async () => {
  upload.mockResolvedValue({ import_type: "workforce_schedule", source: "attendance_sheet", filename: "escala.xlsx", competence_month: "2026-08", status: "success_with_warnings", total_records: 3, accepted_records: 2, duplicate_records: 0, rejected_records: 1, conflict_records: 0, unknown_aliases: ["Alias"], issues: [{ code: "unknown_collaborator_alias", message: "Alias não cadastrado.", row: 42, raw_value: "Alias", external_identity: "Alias" }], coverages: [{ dataset: "planned_work_schedules", source: "attendance_sheet", covered_through: "2026-08-31" }] });
  const user = userEvent.setup();
  render(<MemoryRouter initialEntries={["/imports?type=workforce_schedule&competence_month=2026-08"]}><OperationalImportsPage /></MemoryRouter>);
  const input = await screen.findByLabelText("Arquivo operacional");
  await user.upload(input, new File(["xlsx"], "escala.xlsx"));
  await user.click(screen.getByRole("button", { name: "Importar" }));
  expect(upload).toHaveBeenCalledWith("workforce_schedule", expect.any(File), "2026-08");
  expect(await screen.findByText("Importação concluída com inconsistências")).toBeInTheDocument();
  expect(screen.getByText("Alias não cadastrado.")).toBeInTheDocument();
  expect(screen.getByText(/planned_work_schedules/)).toBeInTheDocument();
});

test("shows NOT_READY, empty history and fatal errors", async () => {
  upload.mockRejectedValue(new ApiError({ code: "invalid", message: "Arquivo incompatível", kind: "api" }));
  const user = userEvent.setup();
  render(<MemoryRouter><OperationalImportsPage /></MemoryRouter>);
  await screen.findByText(/Histórico detalhado ainda não está disponível/);
  await user.selectOptions(screen.getByLabelText("Tipo"), "recurrence_mk");
  expect(screen.getByRole("status")).toHaveTextContent("Importação ainda não disponível");
  await user.selectOptions(screen.getByLabelText("Tipo"), "workforce_schedule");
  await user.upload(screen.getByLabelText("Arquivo operacional"), new File(["bad"], "bad.xlsx"));
  await user.click(screen.getByRole("button", { name: "Importar" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("Arquivo incompatível");
});
