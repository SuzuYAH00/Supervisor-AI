import type { ProcessingHealthFilters } from "../types/processing-health";

interface ActiveFiltersProps {
  readonly filters: ProcessingHealthFilters;
}

export function ActiveFilters({ filters }: ActiveFiltersProps) {
  const values = [
    filters.start_date === null ? null : `Início: ${filters.start_date}`,
    filters.end_date === null ? null : `Fim: ${filters.end_date}`,
    filters.source === null ? null : `Origem: ${filters.source}`,
    filters.rules_engine_version === null
      ? null
      : `Versão: ${filters.rules_engine_version}`,
  ].filter((value): value is string => value !== null);

  return (
    <section className="filter-summary" aria-label="Filtros aplicados">
      <strong>Escopo consultado</strong>
      {values.length === 0 ? (
        <span>Todo o histórico persistido</span>
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
