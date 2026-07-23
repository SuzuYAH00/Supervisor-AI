import type { ApiError } from "../../lib/http/api-error";

interface ErrorStateProps {
  readonly error: ApiError;
  readonly onRetry: () => void;
}

export function ErrorState({ error, onRetry }: ErrorStateProps) {
  const connectionFailure = error.kind === "network";
  return (
    <section className="feedback-state error-state" role="alert">
      <p className="eyebrow">Não foi possível atualizar os dados</p>
      <h2>
        {connectionFailure
          ? "O backend está indisponível"
          : "A consulta não pôde ser concluída"}
      </h2>
      <p>{error.message}</p>
      <button className="primary-button" type="button" onClick={onRetry}>
        Tentar novamente
      </button>
    </section>
  );
}
