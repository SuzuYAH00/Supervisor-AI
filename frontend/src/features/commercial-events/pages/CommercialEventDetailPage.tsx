import { Link, useParams } from "react-router-dom";

import { ErrorState } from "../../../components/feedback/ErrorState";
import { InvalidRouteState } from "../../../components/feedback/InvalidRouteState";
import { LoadingState } from "../../../components/feedback/LoadingState";
import { NotFoundState } from "../../../components/feedback/NotFoundState";
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
        <InvalidRouteState
          title="Rota de evento inválida"
          description="O identificador do evento deve ser informado."
        />
      ) : null}
      {detail.isLoading ? (
        <LoadingState
          title="Carregando detalhes do evento"
          description={`Consultando ${commercialEventId ?? "o evento"}.`}
        />
      ) : null}
      {!detail.isLoading && isNotFound ? (
        <NotFoundState
          title="Evento comercial não encontrado"
          description="Não existe um evento persistido com esse identificador."
          action={{ label: "Tentar novamente", onClick: detail.refetch }}
        />
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
