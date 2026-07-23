import { Link, useParams } from "react-router-dom";

import { ErrorState } from "../../../components/feedback/ErrorState";
import { LoadingState } from "../../../components/feedback/LoadingState";
import { ProcessingRunDetails } from "../components/ProcessingRunDetails";
import { useProcessingRunDetail } from "../hooks/use-processing-run-detail";

export function ProcessingRunDetailPage() {
  const { processingRunId } = useParams<{ processingRunId: string }>();
  const detail = useProcessingRunDetail(processingRunId);
  const isNotFound =
    detail.error?.status === 404 &&
    detail.error.code === "processing_run_not_found";

  return (
    <section className="page-section" aria-labelledby="run-detail-title">
      <div className="page-header">
        <div>
          <p className="eyebrow">Processamento</p>
          <h1 id="run-detail-title">Detalhes da execução</h1>
          <p className="page-description">
            Consulte a execução, o evento relacionado e as fases públicas
            persistidas, sem reprocessamento.
          </p>
          <p className="identifier-cell">
            Execução consultada: {processingRunId ?? "—"}
          </p>
        </div>
        <Link className="button button--secondary" to="/processing-runs">
          Voltar para execuções
        </Link>
      </div>

      {detail.isInvalidId ? (
        <section className="feedback-state error-state" role="alert">
          <h2>Rota de execução inválida</h2>
          <p>O identificador da execução deve ser informado.</p>
        </section>
      ) : null}

      {detail.isLoading ? (
        <LoadingState
          title="Carregando detalhes da execução"
          description={`Consultando ${processingRunId ?? "a execução"}.`}
        />
      ) : null}

      {!detail.isLoading && isNotFound ? (
        <section className="feedback-state error-state" role="alert">
          <p className="eyebrow">Execução não encontrada</p>
          <h2>A execução não foi localizada</h2>
          <p>Não existe uma Processing Run persistida com esse identificador.</p>
          <button
            className="primary-button"
            type="button"
            onClick={detail.refetch}
          >
            Tentar novamente
          </button>
        </section>
      ) : null}

      {!detail.isLoading &&
      detail.error !== null &&
      !isNotFound ? (
        <ErrorState error={detail.error} onRetry={detail.refetch} />
      ) : null}

      {!detail.isLoading &&
      detail.error === null &&
      detail.data !== null ? (
        <ProcessingRunDetails detail={detail.data} />
      ) : null}
    </section>
  );
}
