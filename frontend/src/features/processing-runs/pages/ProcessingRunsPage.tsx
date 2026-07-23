import { ErrorState } from "../../../components/feedback/ErrorState";
import { LoadingState } from "../../../components/feedback/LoadingState";
import { CursorPagination } from "../components/CursorPagination";
import { ProcessingRunsTable } from "../components/ProcessingRunsTable";
import { useProcessingRuns } from "../hooks/use-processing-runs";

export function ProcessingRunsPage() {
  const listing = useProcessingRuns();

  return (
    <section className="page-section" aria-labelledby="processing-runs-title">
      <div className="page-header">
        <div>
          <p className="eyebrow">Processamento</p>
          <h1 id="processing-runs-title">Execuções de processamento</h1>
          <p className="page-description">
            Consulte as execuções persistidas pelo pipeline na ordem fornecida
            pela API.
          </p>
        </div>
        <button
          className="button button--secondary"
          type="button"
          onClick={listing.refetch}
          disabled={listing.isLoading}
        >
          Atualizar
        </button>
      </div>

      {listing.isLoading ? (
        <LoadingState
          title="Carregando execuções"
          description={`Consultando a página ${listing.sessionPage} desta sessão.`}
        />
      ) : null}

      {!listing.isLoading && listing.error !== null ? (
        <>
          <ErrorState error={listing.error} onRetry={listing.refetch} />
          {listing.canGoPrevious ? (
            <CursorPagination
              sessionPage={listing.sessionPage}
              canGoNext={false}
              canGoPrevious={listing.canGoPrevious}
              onNext={listing.goNext}
              onPrevious={listing.goPrevious}
            />
          ) : null}
        </>
      ) : null}

      {!listing.isLoading &&
      listing.error === null &&
      listing.data !== null ? (
        <>
          {listing.data.items.length === 0 ? (
            <div className="empty-state" role="status">
              <h2>Nenhuma execução encontrada</h2>
              <p>Nenhuma execução de processamento foi encontrada.</p>
            </div>
          ) : (
            <ProcessingRunsTable items={listing.data.items} />
          )}
          <CursorPagination
            sessionPage={listing.sessionPage}
            canGoNext={listing.canGoNext}
            canGoPrevious={listing.canGoPrevious}
            onNext={listing.goNext}
            onPrevious={listing.goPrevious}
          />
        </>
      ) : null}
    </section>
  );
}
