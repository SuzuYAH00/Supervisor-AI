import { Link } from "react-router-dom";

import type { ProcessingRunListItem } from "../types/processing-runs";

interface ProcessingRunsTableProps {
  readonly items: readonly ProcessingRunListItem[];
}

export function ProcessingRunsTable({ items }: ProcessingRunsTableProps) {
  return (
    <div className="table-scroll" tabIndex={0}>
      <table className="data-table">
        <thead>
          <tr>
            <th scope="col">Execução</th>
            <th scope="col">Evento comercial</th>
            <th scope="col">Origem</th>
            <th scope="col">Referência externa</th>
            <th scope="col">Início</th>
            <th scope="col">Conclusão</th>
            <th scope="col">Status final</th>
            <th scope="col">Versão das regras</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.processing_run_id}>
              <td className="identifier-cell">
                <Link
                  to={`/processing-runs/${encodeURIComponent(item.processing_run_id)}`}
                >
                  {item.processing_run_id}
                </Link>
              </td>
              <td className="identifier-cell">{item.event_id}</td>
              <td>{item.source}</td>
              <td className="identifier-cell">{item.external_reference}</td>
              <td>
                <time dateTime={item.started_at}>{item.started_at}</time>
              </td>
              <td>
                <time dateTime={item.completed_at}>{item.completed_at}</time>
              </td>
              <td>{item.final_status}</td>
              <td>{item.rules_engine_version}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
