import { Link, useParams } from "react-router-dom";

import { ErrorState } from "../../../components/feedback/ErrorState";
import { LoadingState } from "../../../components/feedback/LoadingState";
import { CommercialEventDetails } from "../components/CommercialEventDetails";
import { useCommercialEventDetail } from "../hooks/use-commercial-event-detail";

export function CommercialEventDetailPage() {
  const { commercialEventId } = useParams<{ commercialEventId: string }>();
  const detail = useCommercialEventDetail(commercialEventId);
  const isNotFound =
    detail.error?.status === 404 &&
    detail.error.code === "commercial_event_not_found";

  return (
    <section className="page-section" aria-labelledby="event-detail-title">
      <div className="page-header">
        <div>
          <p className="eyebrow">Eventos comerciais</p>
          <h1 id="event-detail-title">Detalhes do evento comercial</h1>
          <p className="page-description">
            Consulte o evento e seus relacionamentos persistidos.
          </p>
        </div>
        <Link className="button button--secondary" to="/commercial-events">
          Voltar para eventos
        </Link>
      </div>

      {detail.isInvalidId ? (
        <section className="feedback-state error-state" role="alert">
          <h2>Rota de evento inválida</h2>
          <p>O identificador do evento deve ser informado.</p>
        </section>
      ) : null}
      {detail.isLoading ? (
        <LoadingState
          title="Carregando detalhes do evento"
          description={`Consultando ${commercialEventId ?? "o evento"}.`}
        />
      ) : null}
      {!detail.isLoading && isNotFound ? (
        <section className="feedback-state error-state" role="alert">
          <h2>Evento comercial não encontrado</h2>
          <p>Não existe um evento persistido com esse identificador.</p>
          <button className="primary-button" type="button" onClick={detail.refetch}>
            Tentar novamente
          </button>
        </section>
      ) : null}
      {!detail.isLoading && detail.error !== null && !isNotFound ? (
        <ErrorState error={detail.error} onRetry={detail.refetch} />
      ) : null}
      {!detail.isLoading && detail.error === null && detail.data !== null ? (
        <CommercialEventDetails detail={detail.data} />
      ) : null}
    </section>
  );
}
