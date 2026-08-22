import { FormEvent, useCallback, useEffect, useState } from "react";
import { ApiError } from "../../../lib/http/api-error";
import { createWorkScheduleOverride, getWorkSchedules } from "../api/work-schedules";
import type { WorkScheduleItem, WorkSchedulesResult } from "../types/work-schedules";

const statusLabel = { resolved_standard: "Expediente padrão", resolved_explicit_grid: "Grade explícita", resolved_override: "Override manual", unresolved: "Pendente" };

export function WorkSchedulesPage() {
  const [month, setMonth] = useState("2026-08");
  const [collaborator, setCollaborator] = useState("");
  const [situation, setSituation] = useState("");
  const [data, setData] = useState<WorkSchedulesResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [version, setVersion] = useState(0);
  const [selected, setSelected] = useState<WorkScheduleItem | null>(null);
  const refresh = useCallback(() => setVersion((value) => value + 1), []);

  useEffect(() => {
    const controller = new AbortController();
    setError(null);
    void getWorkSchedules({ competenceMonth: month, collaboratorId: collaborator || undefined, resolutionStatus: situation || undefined }, controller.signal)
      .then(setData)
      .catch((cause: unknown) => setError(cause instanceof ApiError ? cause.message : "Não foi possível consultar as jornadas."));
    return () => controller.abort();
  }, [month, collaborator, situation, version]);

  async function submitOverride(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selected) return;
    const values = new FormData(event.currentTarget);
    try {
      await createWorkScheduleOverride({ collaborator_id: selected.collaborator_id, work_date: selected.work_date, planned_start: String(values.get("start")), planned_end: String(values.get("end")), reason: String(values.get("reason")) });
      setSelected(null);
      refresh();
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : "Não foi possível criar o override.");
    }
  }

  return <div className="page-stack">
    <header className="page-header"><div><p className="eyebrow">Operação</p><h1>Jornadas</h1><p>Consulte a jornada efetiva e trate pendências sem alterar o expediente padrão.</p></div><div className="pending-summary">Jornadas pendentes: <strong>{data?.pending_count ?? "—"}</strong></div></header>
    <section className="schedule-filters" aria-label="Filtros de jornadas">
      <label>Competência<input type="month" value={month} onChange={(e) => setMonth(e.target.value)} /></label>
      <label>Colaborador<input value={collaborator} onChange={(e) => setCollaborator(e.target.value)} placeholder="collaborator_id" /></label>
      <label>Situação<select value={situation} onChange={(e) => setSituation(e.target.value)}><option value="">Todos</option><option value="pending">Pendentes</option><option value="resolved">Resolvidos</option><option value="with_override">Com override</option></select></label>
    </section>
    {error && <div className="schedule-error" role="alert">{error}</div>}
    <section className="schedule-list" aria-label="Jornadas da competência">
      {data?.items.map((item) => <article className={`schedule-card ${item.resolution_status === "unresolved" ? "pending" : ""}`} key={`${item.collaborator_id}-${item.work_date}`}>
        <div><h2>{item.display_name}</h2><p>{new Date(`${item.work_date}T12:00:00`).toLocaleDateString("pt-BR")}</p></div>
        <div><span className={`status-badge ${item.resolution_status}`}>{statusLabel[item.resolution_status]}</span><strong>{item.planned_start && item.planned_end ? `${item.planned_start.slice(0,5)}–${item.planned_end.slice(0,5)}` : "Jornada pendente"}</strong></div>
        <details><summary>Origem e auditoria</summary><p>Origem efetiva: {item.effective_origin}</p><p>{item.source_sheet} · {item.source_cell}</p><p>Referência: {item.source_reference}</p>{item.unresolved_reason && <p>Motivo: {item.unresolved_reason}</p>}{item.override && <p>Motivo do override: {item.override.reason}</p>}</details>
        {!item.has_override && <button className="secondary-button" type="button" onClick={() => setSelected(item)}>Definir jornada manualmente</button>}
      </article>)}
      {data && data.items.length === 0 && <p>Nenhuma jornada encontrada para os filtros informados.</p>}
    </section>
    {selected && <form className="override-panel" onSubmit={submitOverride}><h2>Definir jornada manualmente</h2><p>{selected.display_name} · {selected.work_date}</p><label>Horário inicial<input required name="start" type="time" /></label><label>Horário final<input required name="end" type="time" /></label><label>Motivo<textarea required name="reason" /></label><div><button type="button" onClick={() => setSelected(null)}>Cancelar</button><button className="primary-button" type="submit">Salvar override</button></div></form>}
  </div>;
}
