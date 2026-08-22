import { FormEvent, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { ApiError } from "../../../lib/http/api-error";
import { createDelayReview, getOperationalDelays } from "../api/delays";
import type { OperationalDelay, OperationalDelaysResult } from "../types/delays";

function clock(seconds: number): string {
  const hours = Math.floor(seconds / 3600).toString().padStart(2, "0");
  const minutes = Math.floor((seconds % 3600) / 60).toString().padStart(2, "0");
  const remainder = (seconds % 60).toString().padStart(2, "0");
  return `${hours}:${minutes}:${remainder}`;
}

export function DelaysPage() {
  const [searchParams] = useSearchParams();
  const [month, setMonth] = useState(searchParams.get("competence_month") ?? "2026-08");
  const [collaborator, setCollaborator] = useState(searchParams.get("collaborator_id") ?? "");
  const [type, setType] = useState("");
  const [status, setStatus] = useState("");
  const [data, setData] = useState<OperationalDelaysResult | null>(null);
  const [selected, setSelected] = useState<OperationalDelay | null>(null);
  const [decision, setDecision] = useState<"valid" | "corrected">("valid");
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [version, setVersion] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setError(null);
    setIsLoading(true);
    void getOperationalDelays({ competenceMonth: month, collaboratorId: collaborator || undefined, delayType: type || undefined, reviewStatus: status || undefined }, controller.signal).then((result) => { setData(result); setIsLoading(false); }).catch((cause: unknown) => { setError(cause instanceof ApiError ? cause.message : "Não foi possível consultar os atrasos."); setIsLoading(false); });
    return () => controller.abort();
  }, [month, collaborator, type, status, version]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selected) return;
    const values = new FormData(event.currentTarget);
    const report = String(values.get("report") ?? "");
    const note = String(values.get("note") ?? "");
    try {
      await createDelayReview(selected.delay_occurrence_id, { decision, ...(report ? { employee_occurrence_report_id: report } : {}), ...(note ? { note } : {}) });
      setSelected(null);
      setVersion((value) => value + 1);
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : "Não foi possível registrar a revisão.");
    }
  }

  return <div className="page-stack">
    <header className="page-header"><div><p className="eyebrow">Operação</p><h1>Revisão de atrasos</h1><p>O formulário é somente possível evidência. Apenas a decisão do supervisor altera a contagem.</p></div></header>
    <section className="delay-summary"><div>Detectados<strong>{data?.detected_count ?? "—"}</strong></div><div>Pendentes<strong>{data?.pending_count ?? "—"}</strong></div><div>Mantidos<strong>{data?.valid_count ?? "—"}</strong></div><div>Corrigidos<strong>{data?.corrected_count ?? "—"}</strong></div></section>
    <section className="schedule-filters" aria-label="Filtros de atrasos"><label>Competência<input type="month" value={month} onChange={(event) => setMonth(event.target.value)} /></label><label>Colaborador<input value={collaborator} onChange={(event) => setCollaborator(event.target.value)} /></label><label>Tipo<select value={type} onChange={(event) => setType(event.target.value)}><option value="">Todos</option><option value="entry">Entrada</option><option value="pause_duration">Pausa</option></select></label><label>Situação<select value={status} onChange={(event) => setStatus(event.target.value)}><option value="">Todos</option><option value="pending_review">Pendentes</option><option value="valid">Mantidos</option><option value="corrected">Corrigidos</option></select></label></section>
    {error && <div className="schedule-error" role="alert">{error}</div>}
    {isLoading && <p role="status">Carregando atrasos...</p>}
    {!isLoading && data?.items.length === 0 && <p>Nenhum atraso encontrado para os filtros informados.</p>}
    <section className="schedule-list" aria-label="Atrasos da competência">{!isLoading && data?.items.map((item) => <article className={`schedule-card ${item.review_status === "pending_review" ? "pending" : ""}`} key={item.delay_occurrence_id}><div><h2>{item.display_name}</h2><p>{new Date(`${item.occurrence_date}T12:00:00`).toLocaleDateString("pt-BR")}</p><span className={`status-badge ${item.review_status}`}>{item.review_status === "pending_review" ? "Pendente — continua contando" : item.review_status === "valid" ? "Mantido" : "Corrigido"}</span></div><div><strong>{item.occurrence_type === "entry" ? "Atraso de entrada" : item.source_fact.pause_type}</strong>{item.occurrence_type === "entry" ? <><p>Jornada: {item.schedule?.planned_start.slice(0,5)}–{item.schedule?.planned_end?.slice(0,5)}</p><p>Primeiro login: {new Date(item.source_fact.started_at).toLocaleTimeString("pt-BR")}</p><p>Limite: {clock(item.applied_limit_seconds)}</p><p>Origem: {item.schedule?.effective_origin}</p></> : <><p>Duração: {clock(item.observed_seconds)}</p><p>Limite: {clock(item.applied_limit_seconds)}</p><p>Fila: {item.source_fact.queue}</p></>}</div><details><summary>Possíveis ocorrências ({item.possible_employee_occurrence_reports.length})</summary>{item.possible_employee_occurrence_reports.length === 0 ? <p>Nenhuma ocorrência declarada no mesmo dia.</p> : item.possible_employee_occurrence_reports.map((report) => <blockquote key={report.id}>{report.reason_text}<small>Enviada em {new Date(report.submitted_at).toLocaleString("pt-BR")}</small></blockquote>)}</details><button className="secondary-button" type="button" onClick={() => setSelected(item)}>{item.review ? "Criar nova revisão" : "Revisar atraso"}</button></article>)}</section>
    {selected && <form className="override-panel" onSubmit={submit}><h2>Registrar decisão</h2><p>Uma nova revisão será adicionada ao histórico. O fato NPX permanece intacto.</p><label>Decisão<select value={decision} onChange={(event) => setDecision(event.target.value as "valid" | "corrected")}><option value="valid">Manter atraso</option><option value="corrected">Corrigir atraso</option></select></label><label>Ocorrência usada como evidência<select name="report" defaultValue=""><option value="">Nenhuma</option>{selected.possible_employee_occurrence_reports.map((report) => <option key={report.id} value={report.id}>{report.reason_text.slice(0,80)}</option>)}</select></label><label>Nota<textarea name="note" /></label><div><button type="button" onClick={() => setSelected(null)}>Cancelar</button><button className="primary-button" type="submit">Salvar revisão</button></div></form>}
  </div>;
}
