import { ErrorState } from "../../../components/feedback/ErrorState";
import { EmptyState } from "../../../components/feedback/EmptyState";
import { LoadingState } from "../../../components/feedback/LoadingState";
import { CollaboratorSummaryList } from "../components/CollaboratorSummaryList";
import { CurrencyTotals } from "../components/CurrencyTotals";
import { FinancialFilters } from "../components/FinancialFilters";
import { useFinancialSummary } from "../hooks/use-financial-summary";

export function FinancialSummaryPage() {
  const { data, error, isLoading, refetch } = useFinancialSummary();

  if (isLoading) {
    return (
      <LoadingState
        title="Carregando resumo financeiro"
        description="Consultando os créditos persistidos no Ledger."
      />
    );
  }
  if (error !== null) {
    return <ErrorState error={error} onRetry={refetch} />;
  }
  if (data === null) {
    return null;
  }

  const isEmpty = data.credit_count === 0;

  return (
    <div className="page-stack">
      <header className="page-header">
        <div>
          <p className="eyebrow">Visão financeira</p>
          <h1>Resumo financeiro</h1>
          <p>
            Consolidação dos créditos persistidos, separada por moeda e
            colaborador.
          </p>
        </div>
        <button className="secondary-button" type="button" onClick={refetch}>
          Atualizar dados
        </button>
      </header>

      <FinancialFilters filters={data.filters} />

      {isEmpty && (
        <EmptyState
          title="Ainda não existem créditos persistidos."
          description="O resumo permanecerá disponível e será atualizado após um lançamento no Ledger."
        />
      )}

      <section className="metrics-grid financial-metrics" aria-label="Resumo geral">
        <article className="metric-card">
          <p>Colaboradores</p>
          <strong>{data.collaborator_count.toLocaleString("pt-BR")}</strong>
          <small>Com créditos no escopo consultado</small>
        </article>
        <article className="metric-card">
          <p>Créditos</p>
          <strong>{data.credit_count.toLocaleString("pt-BR")}</strong>
          <small>Lançamentos consolidados</small>
        </article>
      </section>

      <div className="financial-summary-grid">
        <CurrencyTotals totals={data.totals_by_currency} />
        <CollaboratorSummaryList collaborators={data.collaborators} />
      </div>
    </div>
  );
}
