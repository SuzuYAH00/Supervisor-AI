import { Link } from "react-router-dom";

import type { CsvImportResult as CsvImportResultContract } from "../types/csv-import";

interface CsvImportResultProps {
  readonly result: CsvImportResultContract;
  readonly onNewImport: () => void;
}

interface MetricProps {
  readonly label: string;
  readonly value: number;
}

function Metric({ label, value }: MetricProps) {
  return (
    <article className="metric-card">
      <p>{label}</p>
      <strong>{value}</strong>
    </article>
  );
}

export function CsvImportResult({
  result,
  onNewImport,
}: CsvImportResultProps) {
  return (
    <div className="page-stack">
      <section className="financial-table-card" aria-labelledby="import-result">
        <h2 id="import-result">Resultado da importação</h2>
        <dl className="detail-list">
          <div><dt>Arquivo</dt><dd>{result.file}</dd></div>
          <div><dt>Status</dt><dd>{result.status}</dd></div>
          <div><dt>Início</dt><dd><time dateTime={result.started_at}>{result.started_at}</time></dd></div>
          <div><dt>Conclusão</dt><dd><time dateTime={result.completed_at}>{result.completed_at}</time></dd></div>
          <div><dt>Duração em segundos</dt><dd>{result.duration_seconds}</dd></div>
        </dl>
      </section>

      <section className="metrics-grid" aria-label="Parsing do CSV">
        <Metric label="Linhas de dados" value={result.parsing.total_data_rows} />
        <Metric label="Linhas convertidas" value={result.parsing.converted_rows} />
        <Metric label="Linhas com erro" value={result.parsing.error_rows} />
        <Metric label="Linhas vazias ignoradas" value={result.parsing.ignored_empty_rows} />
      </section>

      <section className="metrics-grid" aria-label="Processamento do CSV">
        <Metric label="Documentos processados" value={result.processing.total_documents} />
        <Metric label="Documentos bem-sucedidos" value={result.processing.successful_documents} />
        <Metric label="Erros de validação" value={result.processing.validation_errors} />
        <Metric label="Conflitos de negócio" value={result.processing.business_conflicts} />
        <Metric label="Erros técnicos" value={result.processing.technical_errors} />
        <Metric label="Processing Runs criadas" value={result.processing.processing_runs_created} />
        <Metric label="Ledger Entries criadas" value={result.processing.ledger_entries_created} />
      </section>

      <section className="financial-table-card" aria-labelledby="import-lines">
        <h2 id="import-lines">Resultados por linha</h2>
        {result.results.length === 0 ? (
          <p className="muted-text">Nenhum resultado de linha foi retornado.</p>
        ) : (
          <div className="table-scroll" tabIndex={0}>
            <table className="data-table">
              <thead>
                <tr>
                  <th scope="col">Linha</th>
                  <th scope="col">Documento</th>
                  <th scope="col">Status</th>
                  <th scope="col">Status final</th>
                  <th scope="col">Processing Run</th>
                  <th scope="col">Evento comercial</th>
                  <th scope="col">Ledger Entry</th>
                  <th scope="col">Erro</th>
                </tr>
              </thead>
              <tbody>
                {result.results.map((row) => (
                  <tr key={`${row.line_number}-${row.document_identifier ?? ""}`}>
                    <td>{row.line_number}</td>
                    <td>{row.document_identifier ?? "—"}</td>
                    <td>{row.status}</td>
                    <td>{row.final_status ?? "—"}</td>
                    <td className="identifier-cell">
                      {row.processing_run_id === null ? (
                        "—"
                      ) : (
                        <Link
                          to={`/processing-runs/${encodeURIComponent(row.processing_run_id)}`}
                        >
                          {row.processing_run_id}
                        </Link>
                      )}
                    </td>
                    <td className="identifier-cell">
                      {row.commercial_event_id ?? "—"}
                    </td>
                    <td className="identifier-cell">
                      {row.ledger_entry_id ?? "—"}
                    </td>
                    <td>{row.error_message ?? row.error_type ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <button className="secondary-button" type="button" onClick={onNewImport}>
        Nova importação
      </button>
    </div>
  );
}
