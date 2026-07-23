import type { CommercialEventListItem } from "../types/commercial-events";

interface CommercialEventsTableProps {
  readonly items: readonly CommercialEventListItem[];
}

export function CommercialEventsTable({ items }: CommercialEventsTableProps) {
  return (
    <section className="financial-table-card" aria-labelledby="events-list">
      <header>
        <h2 id="events-list">Eventos persistidos</h2>
        <p>Entradas comerciais factuais na ordem fornecida pela API.</p>
      </header>
      <div className="table-scroll">
        <table className="events-table">
          <thead>
            <tr>
              <th scope="col">Evento</th>
              <th scope="col">Referência externa</th>
              <th scope="col">Origem</th>
              <th scope="col">Ocorrido em</th>
              <th scope="col">Recebido em</th>
              <th scope="col">Criado em</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.event_id}>
                <th className="identifier-cell" scope="row">
                  {item.event_id}
                </th>
                <td className="identifier-cell">{item.external_reference}</td>
                <td>{item.source}</td>
                <td>
                  <time dateTime={item.occurred_at}>{item.occurred_at}</time>
                </td>
                <td>
                  <time dateTime={item.received_at}>{item.received_at}</time>
                </td>
                <td>
                  <time dateTime={item.created_at}>{item.created_at}</time>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
