interface LoadingStateProps {
  readonly title?: string;
  readonly description?: string;
}

export function LoadingState({
  title = "Carregando saúde do processamento",
  description = "Consultando os dados persistidos no Supervisor AI.",
}: LoadingStateProps) {
  return (
    <section className="feedback-state" aria-live="polite" aria-busy="true">
      <div className="loading-indicator" aria-hidden="true" />
      <h2>{title}</h2>
      <p>{description}</p>
    </section>
  );
}
