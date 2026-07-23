import type { FinancialTimelineItem } from "../types/financial-timeline";

interface FinancialTimelineTableProps {
  readonly items: readonly FinancialTimelineItem[];
}

export function FinancialTimelineTable({
  items,
}: FinancialTimelineTableProps) {
  return (
    <section className="financial-table-card" aria-labelledby="timeline-list">
      <header>
        <h2 id="timeline-list">Lançamentos financeiros</h2>
        <p>Registros do Ledger na ordem retornada pela API.</p>
      </header>
      <div className="table-scroll">
        <table className="timeline-table">
          <thead>
            <tr>
              <th scope="col">Lançamento</th>
              <th scope="col">Publicado em</th>
              <th scope="col">Tipo</th>
              <th scope="col">Moeda</th>
              <th scope="col">Valor</th>
              <th scope="col">Fatura</th>
              <th scope="col">Referência de posting</th>
              <th scope="col">Referência de cálculo</th>
              <th scope="col">Referências de origem</th>
              <th scope="col">Evento</th>
              <th scope="col">Referência externa</th>
              <th scope="col">Origem do evento</th>
              <th scope="col">Evento ocorrido em</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.ledger_entry_id}>
                <th className="identifier-cell" scope="row">
                  {item.ledger_entry_id}
                </th>
                <td>
                  <time dateTime={item.posted_at}>{item.posted_at}</time>
                </td>
                <td>{item.entry_type}</td>
                <td>{item.currency}</td>
                <td>{item.amount}</td>
                <td className="identifier-cell">{item.invoice_id ?? "—"}</td>
                <td className="identifier-cell">{item.posting_reference}</td>
                <td className="identifier-cell">
                  {item.remuneration_calculation_reference}
                </td>
                <td className="identifier-cell">
                  {item.source_reference_ids.length === 0
                    ? "—"
                    : item.source_reference_ids.join(", ")}
                </td>
                <td className="identifier-cell">
                  {item.commercial_event.event_id}
                </td>
                <td className="identifier-cell">
                  {item.commercial_event.external_reference}
                </td>
                <td>{item.commercial_event.source}</td>
                <td>
                  <time dateTime={item.commercial_event.occurred_at}>
                    {item.commercial_event.occurred_at}
                  </time>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
