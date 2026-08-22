import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ApiError } from "../../../lib/http/api-error";
import { getVariableCompensation } from "../api/variable-compensation";
import type { VariableCompensationResult } from "../types/variable-compensation";
import type { ClosurePendingIssue } from "../types/variable-compensation";

const money = (value: string | null) => value === null ? "PENDENTE" : new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" }).format(Number(value));
const tier = (value: string | null) => value === null ? "Sem faixa" : ({ gold: "Ouro", silver: "Prata", bronze: "Bronze" }[value] ?? value);
const percent = (value: string | null) => value === null ? "—" : `${(Number(value) * 100).toFixed(2)}%`;
const componentLabel = { presence: "Presença", csat: "CSAT", recurrence: "Reincidência", delays: "Atrasos", work_schedule: "Jornadas" };

function issueTarget(issue: ClosurePendingIssue, month: string): string | null {
  if (!issue.action_target) return null;
  const parameters = new URLSearchParams({ competence_month: month });
  if (issue.collaborator_id) parameters.set("collaborator_id", issue.collaborator_id);
  if (issue.component === "work_schedule") parameters.set("resolution_status", "pending");
  return `${issue.action_target}?${parameters}`;
}

function IssueList({ issues, month }: { issues: readonly ClosurePendingIssue[]; month: string }) {
  return <ul className="issue-list">{issues.map((issue) => { const target = issueTarget(issue, month); return <li key={`${issue.code}-${issue.collaborator_id ?? "competence"}`}><div><strong>{componentLabel[issue.component]}</strong><p>{issue.message}</p><small>{issue.scope === "competence" ? `Afeta ${issue.affected_collaborator_ids.length} colaborador(es)` : issue.collaborator_id}</small></div>{target ? <Link to={target}>{issue.component === "work_schedule" ? "Resolver jornadas" : "Ver detalhes"}</Link> : <span>Requer importação ou configuração</span>}</li>; })}</ul>;
}

export function VariableCompensationPage() {
  const [month, setMonth] = useState("2026-08");
  const [collaborator, setCollaborator] = useState("");
  const [status, setStatus] = useState("");
  const [data, setData] = useState<VariableCompensationResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { const controller = new AbortController(); setLoading(true); setError(null); void getVariableCompensation({ competenceMonth: month, collaboratorId: collaborator || undefined, status: status || undefined }, controller.signal).then((value) => { setData(value); setLoading(false); }).catch((cause: unknown) => { setError(cause instanceof ApiError ? cause.message : "Não foi possível consultar a renda variável."); setLoading(false); }); return () => controller.abort(); }, [month, collaborator, status]);
  return <div className="page-stack">
    <header className="page-header"><div><p className="eyebrow">Fechamento mensal</p><h1>Renda Variável</h1><p>Composição explicável dos indicadores já calculados pelo motor de regras.</p></div></header>
    <section className="delay-summary"><div>Colaboradores<strong>{data?.collaborator_count ?? "—"}</strong></div><div>Calculados<strong>{data?.calculated_count ?? "—"}</strong></div><div>Com pendências<strong>{data?.incomplete_count ?? "—"}</strong></div><div>Total projetado<strong>{money(data?.projected_total ?? null)}</strong></div></section>
    <section className="issues-center" aria-label="Pendências da competência"><header><div><p className="eyebrow">Pendências da competência</p><h2>{data?.issue_summary.blocking_count ?? "—"} pendências bloqueantes</h2></div></header>{!loading && data?.issues.length === 0 ? <p>Nenhuma pendência bloqueante nesta competência.</p> : <IssueList issues={data?.issues ?? []} month={month} />}</section>
    <section className="schedule-filters" aria-label="Filtros da renda variável"><label>Competência<input type="month" value={month} onChange={(event) => setMonth(event.target.value)} /></label><label>Colaborador<input value={collaborator} onChange={(event) => setCollaborator(event.target.value)} /></label><label>Situação<select value={status} onChange={(event) => setStatus(event.target.value)}><option value="">Todos</option><option value="calculated">Calculados</option><option value="incomplete">Com pendências</option></select></label></section>
    {error && <div className="schedule-error" role="alert">{error}</div>}
    {loading && <p role="status">Carregando fechamento...</p>}
    {!loading && data?.items.length === 0 && <p>Nenhum colaborador encontrado para os filtros informados.</p>}
    <section className="rv-list" aria-label="Fechamentos da competência">{!loading && data?.items.map((item) => <article className={`rv-card ${item.status}`} key={item.collaborator_id}><header><div><h2>{item.display_name}</h2><span className={`status-badge ${item.status}`}>{item.status === "calculated" ? "Calculado" : "Com pendências"}</span></div><strong>{money(item.total_amount)}</strong></header>{item.pending_issues.length > 0 && <div className="rv-pending"><strong>Fechamento pendente</strong><IssueList issues={item.pending_issues} month={month} /></div>}<div className="rv-components"><section><h3>CSAT · {item.csat.modality}</h3><p>{tier(item.csat.tier)} · {money(item.csat.amount)}</p><small>Nota {item.csat.individual_value ?? "—"} · média {item.csat.team_average ?? "—"}</small><small>Respondentes {percent(item.csat.response_rate)} · mínimo {percent(item.csat.minimum_response_rate)}</small></section><section><h3>Reincidência</h3><p>{tier(item.recurrence.tier)} · {money(item.recurrence.amount)}</p><small>Taxa {percent(item.recurrence.individual_value)} · média {percent(item.recurrence.team_average)}</small></section><section><h3>Atrasos</h3><p>{item.delays.count ?? "Pendente"} · {money(item.delays.amount)}</p><Link to={`/delays?competence_month=${month}&collaborator_id=${encodeURIComponent(item.collaborator_id)}`}>Revisar atrasos</Link></section><section><h3>Ausências</h3><p>{item.absences.count ?? "Pendente"} · {money(item.absences.amount)}</p></section></div>{item.status === "calculated" && <footer><span>Positivos {money(item.positive_amount)}</span><span>Descontos {money(item.deductions_amount)}</span><strong>Total {money(item.total_amount)}</strong></footer>}</article>)}</section>
  </div>;
}
