import { ErrorState } from "../../../components/feedback/ErrorState";
import { EmptyState } from "../../../components/feedback/EmptyState";
import { LoadingState } from "../../../components/feedback/LoadingState";
import { ActiveFilters } from "../components/ActiveFilters";
import { DistributionList } from "../components/DistributionList";
import { MetricCard } from "../components/MetricCard";
import { useProcessingHealth } from "../hooks/use-processing-health";

export function ProcessingHealthPage() {
  const { data, error, isLoading, refetch } = useProcessingHealth();

  if (isLoading) {
    return <LoadingState />;
  }
  if (error !== null) {
    return <ErrorState error={error} onRetry={refetch} />;
  }
  if (data === null) {
    return null;
  }

  const eventsConsidered =
    data.commercial_events.events_with_processing_runs +
    data.commercial_events.events_without_processing_runs;
  const isEmpty = data.processing_runs.total === 0;

  return (
    <div className="page-stack">
      <header className="page-header">
        <div>
          <p className="eyebrow">Visão operacional</p>
          <h1>Saúde do processamento</h1>
          <p>
            Métricas factuais das execuções e eventos persistidos. Nenhum
            diagnóstico é calculado nesta tela.
          </p>
        </div>
        <button className="secondary-button" type="button" onClick={refetch}>
          Atualizar dados
        </button>
      </header>

      <ActiveFilters filters={data.filters} />

      {isEmpty && (
        <EmptyState
          title="Ainda não existem processamentos persistidos."
          description="As métricas permanecerão disponíveis e serão atualizadas após a primeira importação."
        />
      )}

      <section className="metrics-grid" aria-label="Métricas principais">
        <MetricCard
          label="Execuções"
          value={data.processing_runs.total}
          description="Processing Runs persistidas"
        />
        <MetricCard
          label="Eventos considerados"
          value={eventsConsidered}
          description="Com e sem execução"
        />
        <MetricCard
          label="Eventos com Ledger"
          value={data.commercial_events.events_with_ledger_entries}
          description="Com pelo menos um lançamento"
        />
        <MetricCard
          label="Eventos sem Ledger"
          value={data.commercial_events.events_without_ledger_entries}
          description="Não representa falha automaticamente"
        />
        <MetricCard
          label="Eventos reprocessados"
          value={data.commercial_events.events_with_multiple_processing_runs}
          description="Com mais de uma execução"
        />
      </section>

      <div className="distribution-grid">
        <DistributionList
          title="Status finais"
          description="Contagem pelo status persistido da execução."
          items={data.processing_runs.by_final_status.map((item) => ({
            key: item.final_status,
            label: item.final_status,
            count: item.count,
          }))}
        />
        <DistributionList
          title="Versões do Rules Engine"
          description="Execuções agrupadas pela versão persistida."
          items={data.processing_runs.by_rules_engine_version.map((item) => ({
            key: item.rules_engine_version,
            label: item.rules_engine_version,
            count: item.count,
          }))}
        />
      </div>
    </div>
  );
}
