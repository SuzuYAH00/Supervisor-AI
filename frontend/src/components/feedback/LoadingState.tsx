export function LoadingState() {
  return (
    <section className="feedback-state" aria-live="polite" aria-busy="true">
      <div className="loading-indicator" aria-hidden="true" />
      <h2>Carregando saúde do processamento</h2>
      <p>Consultando os dados persistidos no Supervisor AI.</p>
    </section>
  );
}
