import type { FinancialSummaryFilters } from "../types/financial-summary";

interface FinancialFiltersProps {
  readonly filters: FinancialSummaryFilters;
}

export function FinancialFilters({ filters }: FinancialFiltersProps) {
  const values = [
    filters.collaborator_id === null
      ? null
      : `Colaborador: ${filters.collaborator_id}`,
    filters.start_date === null ? null : `Início: ${filters.start_date}`,
    filters.end_date === null ? null : `Fim: ${filters.end_date}`,
  ].filter((value): value is string => value !== null);

  return (
    <section className="filter-summary" aria-label="Filtros financeiros aplicados">
      <strong>Escopo consultado</strong>
      {values.length === 0 ? (
        <span>Todo o histórico financeiro persistido</span>
      ) : (
        <ul>
          {values.map((value) => (
            <li key={value}>{value}</li>
          ))}
        </ul>
      )}
    </section>
  );
}
