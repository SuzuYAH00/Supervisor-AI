import { ErrorState } from "../../../components/feedback/ErrorState";
import { EmptyState } from "../../../components/feedback/EmptyState";
import { LoadingState } from "../../../components/feedback/LoadingState";
import { CommercialEventsTable } from "../components/CommercialEventsTable";
import { CursorPagination } from "../components/CursorPagination";
import { useCommercialEvents } from "../hooks/use-commercial-events";

export function CommercialEventsPage() {
  const {
    data,
    error,
    isLoading,
    sessionPage,
    canGoNext,
    canGoPrevious,
    goNext,
    goPrevious,
    refetch,
  } = useCommercialEvents();

  return (
    <div className="page-stack">
      <header className="page-header">
        <div>
          <p className="eyebrow">Auditoria comercial</p>
          <h1>Eventos comerciais</h1>
          <p>
            Entradas persistidas pelo pipeline, sem cálculos ou estados
            derivados no frontend.
          </p>
        </div>
        <button
          className="secondary-button"
          type="button"
          disabled={isLoading}
          onClick={refetch}
        >
          Atualizar dados
        </button>
      </header>

      {isLoading && (
        <LoadingState
          title="Carregando eventos comerciais"
          description={`Consultando a página ${sessionPage} desta sessão.`}
        />
      )}

      {!isLoading && error !== null && (
        <>
          <ErrorState error={error} onRetry={refetch} />
          {canGoPrevious && (
            <button
              className="secondary-button previous-after-error"
              type="button"
              onClick={goPrevious}
            >
              Voltar à página anterior
            </button>
          )}
        </>
      )}

      {!isLoading && error === null && data !== null && (
        <>
          {data.items.length === 0 ? (
            <EmptyState
              title="Nenhum evento comercial foi encontrado."
              description="A consulta foi concluída sem registros neste escopo."
            />
          ) : (
            <CommercialEventsTable items={data.items} />
          )}
          <CursorPagination
            sessionPage={sessionPage}
            canGoNext={canGoNext}
            canGoPrevious={canGoPrevious}
            isLoading={isLoading}
            onNext={goNext}
            onPrevious={goPrevious}
          />
        </>
      )}
    </div>
  );
}
