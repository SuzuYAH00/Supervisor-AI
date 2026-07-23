import type { ProcessingRunDetailResponse } from "../types/processing-run-detail";

interface ProcessingRunDetailsProps {
  readonly detail: ProcessingRunDetailResponse;
}

interface FactProps {
  readonly label: string;
  readonly value: string;
  readonly dateTime?: boolean;
}

function Fact({ label, value, dateTime = false }: FactProps) {
  return (
    <div>
      <dt>{label}</dt>
      <dd className="identifier-cell">
        {dateTime ? <time dateTime={value}>{value}</time> : value}
      </dd>
    </div>
  );
}

export function ProcessingRunDetails({ detail }: ProcessingRunDetailsProps) {
  const run = detail.processing_run;
  const event = detail.commercial_event;

  return (
    <div className="detail-sections">
      <section
        className="financial-table-card"
        aria-labelledby="run-metadata-title"
      >
        <h2 id="run-metadata-title">Execução persistida</h2>
        <dl className="detail-list">
          <Fact label="Identificador" value={run.processing_run_id} />
          <Fact label="Evento comercial" value={run.event_id} />
          <Fact label="Status final" value={run.final_status} />
          <Fact label="Início" value={run.started_at} dateTime />
          <Fact label="Conclusão" value={run.completed_at} dateTime />
          <Fact label="Versão das regras" value={run.rules_engine_version} />
          <Fact label="Criação" value={run.created_at} dateTime />
        </dl>
      </section>

      <section className="financial-table-card" aria-labelledby="run-event-title">
        <h2 id="run-event-title">Evento comercial relacionado</h2>
        <dl className="detail-list">
          <Fact label="Identificador" value={event.event_id} />
          <Fact label="Referência externa" value={event.external_reference} />
          <Fact label="Origem" value={event.source} />
          <Fact label="Ocorrência" value={event.occurred_at} dateTime />
        </dl>
      </section>

      <section className="financial-table-card" aria-labelledby="run-phases-title">
        <h2 id="run-phases-title">Fases persistidas</h2>
        {detail.phases.length === 0 ? (
          <p className="muted-text">Nenhuma fase pública foi persistida.</p>
        ) : (
          <div className="table-scroll" tabIndex={0}>
            <table className="data-table">
              <thead>
                <tr>
                  <th scope="col">Fase</th>
                  <th scope="col">Status</th>
                  <th scope="col">Pode continuar</th>
                </tr>
              </thead>
              <tbody>
                {detail.phases.map((phase, index) => (
                  <tr key={`${phase.phase}-${index}`}>
                    <td>{phase.phase}</td>
                    <td>{phase.status}</td>
                    <td>{String(phase.can_continue)}</td>
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
