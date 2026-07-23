import type { CollaboratorFinancialSummary } from "../types/financial-summary";

interface CollaboratorSummaryListProps {
  readonly collaborators: readonly CollaboratorFinancialSummary[];
}

export function CollaboratorSummaryList({
  collaborators,
}: CollaboratorSummaryListProps) {
  const orderedCollaborators = [...collaborators].sort((left, right) =>
    left.collaborator_id.localeCompare(right.collaborator_id),
  );

  return (
    <section className="financial-table-card" aria-labelledby="collaborator-list">
      <header>
        <h2 id="collaborator-list">Colaboradores</h2>
        <p>Créditos e valores consolidados por moeda.</p>
      </header>
      {orderedCollaborators.length === 0 ? (
        <p className="empty-list">Nenhum colaborador com créditos persistidos.</p>
      ) : (
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th scope="col">Colaborador</th>
                <th scope="col">Moeda</th>
                <th scope="col">Valor</th>
                <th scope="col">Créditos</th>
                <th scope="col">Posição na moeda</th>
                <th scope="col">Participação na moeda</th>
              </tr>
            </thead>
            <tbody>
              {orderedCollaborators.flatMap((collaborator) =>
                [...collaborator.totals_by_currency]
                  .sort((left, right) =>
                    left.currency.localeCompare(right.currency),
                  )
                  .map((total) => (
                    <tr
                      key={`${collaborator.collaborator_id}:${total.currency}`}
                    >
                      <th scope="row">{collaborator.collaborator_id}</th>
                      <td>{total.currency}</td>
                      <td>{total.amount}</td>
                      <td>{total.credit_count}</td>
                      <td>{total.rank}</td>
                      <td>{total.share_percentage}%</td>
                    </tr>
                  )),
              )}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
