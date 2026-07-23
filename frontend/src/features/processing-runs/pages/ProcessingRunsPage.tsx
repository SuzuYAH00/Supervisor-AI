import { ErrorState } from "../../../components/feedback/ErrorState";
import { LoadingState } from "../../../components/feedback/LoadingState";
import { CursorPagination } from "../components/CursorPagination";
import { ProcessingRunsTable } from "../components/ProcessingRunsTable";
import { useProcessingRuns } from "../hooks/use-processing-runs";

export function ProcessingRunsPage() {
  const timeline = useProcessingRuns();

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
          onClick={timeline.refetch}
          disabled={timeline.isLoading}
        >
          Atualizar
        </button>
      </div>

      {timeline.isLoading ? (
        <LoadingState
          title="Carregando execuções"
          description={`Consultando a página ${timeline.sessionPage} desta sessão.`}
        />
      ) : null}

      {!timeline.isLoading && timeline.error !== null ? (
        <>
          <ErrorState error={timeline.error} onRetry={timeline.refetch} />
          {timeline.canGoPrevious ? (
            <CursorPagination
              sessionPage={timeline.sessionPage}
              canGoNext={false}
              canGoPrevious={timeline.canGoPrevious}
              onNext={timeline.goNext}
              onPrevious={timeline.goPrevious}
            />
          ) : null}
        </>
      ) : null}

      {!timeline.isLoading &&
      timeline.error === null &&
      timeline.data !== null ? (
        <>
          {timeline.data.items.length === 0 ? (
            <div className="empty-state" role="status">
              <h2>Nenhuma execução encontrada</h2>
              <p>Nenhuma execução de processamento foi encontrada.</p>
            </div>
          ) : (
            <ProcessingRunsTable items={timeline.data.items} />
          )}
          <CursorPagination
            sessionPage={timeline.sessionPage}
            canGoNext={timeline.canGoNext}
            canGoPrevious={timeline.canGoPrevious}
            onNext={timeline.goNext}
            onPrevious={timeline.goPrevious}
          />
        </>
      ) : null}
    </section>
  );
}
