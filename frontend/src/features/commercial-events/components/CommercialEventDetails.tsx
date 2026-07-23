import { Link } from "react-router-dom";

import type { CommercialEventDetailResponse } from "../types/commercial-event-detail";

interface CommercialEventDetailsProps {
  readonly detail: CommercialEventDetailResponse;
}

export function CommercialEventDetails({
  detail,
}: CommercialEventDetailsProps) {
  const event = detail.commercial_event;
  return (
    <div className="detail-sections">
      <section className="financial-table-card" aria-labelledby="event-facts">
        <h2 id="event-facts">Evento persistido</h2>
        <dl className="detail-list">
          <div><dt>Identificador</dt><dd>{event.event_id}</dd></div>
          <div><dt>Referência externa</dt><dd>{event.external_reference}</dd></div>
          <div><dt>Origem</dt><dd>{event.source}</dd></div>
          <div><dt>Ocorrência</dt><dd><time dateTime={event.occurred_at}>{event.occurred_at}</time></dd></div>
          <div><dt>Recebimento</dt><dd><time dateTime={event.received_at}>{event.received_at}</time></dd></div>
          <div><dt>Criação</dt><dd><time dateTime={event.created_at}>{event.created_at}</time></dd></div>
        </dl>
      </section>

      <section className="financial-table-card" aria-labelledby="event-runs">
        <h2 id="event-runs">Execuções relacionadas</h2>
        {detail.processing_runs.length === 0 ? (
          <p className="muted-text">Nenhuma execução relacionada.</p>
        ) : (
          <div className="table-scroll" tabIndex={0}>
            <table className="data-table">
              <thead><tr><th scope="col">Execução</th><th scope="col">Status final</th><th scope="col">Início</th><th scope="col">Conclusão</th><th scope="col">Versão das regras</th><th scope="col">Criação</th></tr></thead>
              <tbody>
                {detail.processing_runs.map((run) => (
                  <tr key={run.processing_run_id}>
                    <td className="identifier-cell">
                      <Link to={`/processing-runs/${encodeURIComponent(run.processing_run_id)}`}>
                        {run.processing_run_id}
                      </Link>
                    </td>
                    <td>{run.final_status}</td>
                    <td><time dateTime={run.started_at}>{run.started_at}</time></td>
                    <td><time dateTime={run.completed_at}>{run.completed_at}</time></td>
                    <td>{run.rules_engine_version}</td>
                    <td><time dateTime={run.created_at}>{run.created_at}</time></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="financial-table-card" aria-labelledby="event-ledger">
        <h2 id="event-ledger">Lançamentos relacionados</h2>
        {detail.ledger_entries.length === 0 ? (
          <p className="muted-text">Nenhum lançamento relacionado.</p>
        ) : (
          <div className="table-scroll" tabIndex={0}>
            <table className="data-table">
              <thead><tr><th scope="col">Lançamento</th><th scope="col">Beneficiário</th><th scope="col">Tipo</th><th scope="col">Valor</th><th scope="col">Moeda</th><th scope="col">Postado em</th><th scope="col">Referência</th><th scope="col">Cálculo</th><th scope="col">Fatura</th><th scope="col">Referências de origem</th></tr></thead>
              <tbody>
                {detail.ledger_entries.map((entry) => (
                  <tr key={entry.ledger_entry_id}>
                    <td className="identifier-cell">{entry.ledger_entry_id}</td>
                    <td>{entry.beneficiary_id}</td>
                    <td>{entry.entry_type}</td>
                    <td>{entry.amount}</td>
                    <td>{entry.currency}</td>
                    <td><time dateTime={entry.posted_at}>{entry.posted_at}</time></td>
                    <td className="identifier-cell">{entry.posting_reference}</td>
                    <td className="identifier-cell">{entry.remuneration_calculation_reference}</td>
                    <td>{entry.invoice_id ?? "—"}</td>
                    <td>{entry.source_reference_ids.length === 0 ? "—" : entry.source_reference_ids.join(", ")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
