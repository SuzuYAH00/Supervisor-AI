import { ErrorState } from "../../../components/feedback/ErrorState";
import { EmptyState } from "../../../components/feedback/EmptyState";
import { LoadingState } from "../../../components/feedback/LoadingState";
import { CursorPagination } from "../components/CursorPagination";
import { FinancialTimelineSearch } from "../components/FinancialTimelineSearch";
import { FinancialTimelineTable } from "../components/FinancialTimelineTable";
import { useFinancialTimeline } from "../hooks/use-financial-timeline";

export function FinancialTimelinePage() {
  const timeline = useFinancialTimeline();

  return (
    <div className="page-stack">
      <header className="page-header">
        <div>
          <p className="eyebrow">Ledger por colaborador</p>
          <h1>Timeline financeira</h1>
          <p>
            Lançamentos financeiros persistidos e seus eventos comerciais de
            origem.
          </p>
        </div>
      </header>

      <FinancialTimelineSearch
        submittedCollaboratorId={timeline.submittedCollaboratorId}
        isLoading={timeline.isLoading}
        onSubmit={timeline.submitCollaborator}
      />

      {!timeline.hasSearched && (
        <EmptyState
          title="Informe um colaborador para iniciar a consulta."
          description="A timeline não é carregada enquanto o formulário não for enviado."
        />
      )}

      {timeline.isLoading && timeline.submittedCollaboratorId !== null && (
        <LoadingState
          title={`Carregando timeline de ${timeline.submittedCollaboratorId}`}
          description={`Consultando a página ${timeline.sessionPage} desta consulta.`}
        />
      )}

      {!timeline.isLoading && timeline.error !== null && (
        <ErrorState error={timeline.error} onRetry={timeline.refetch} />
      )}

      {!timeline.isLoading &&
        timeline.error !== null &&
        timeline.canGoPrevious && (
          <button
            className="secondary-button previous-after-error"
            type="button"
            onClick={timeline.goPrevious}
          >
            Voltar à página anterior
          </button>
        )}

      {!timeline.isLoading &&
        timeline.error === null &&
        timeline.data !== null && (
          <>
            {timeline.data.items.length === 0 ? (
              <EmptyState
                title="Nenhum lançamento financeiro foi encontrado."
                description={`A consulta de ${timeline.data.collaborator_id} foi concluída sem registros.`}
              />
            ) : (
              <FinancialTimelineTable items={timeline.data.items} />
            )}
            <CursorPagination
              sessionPage={timeline.sessionPage}
              canGoNext={timeline.canGoNext}
              canGoPrevious={timeline.canGoPrevious}
              onNext={timeline.goNext}
              onPrevious={timeline.goPrevious}
            />
          </>
        )}
    </div>
  );
}
