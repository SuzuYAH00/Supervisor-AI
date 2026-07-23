import { Link } from "react-router-dom";

export function NotFoundPage() {
  return (
    <section className="not-found">
      <p className="eyebrow">Página não encontrada</p>
      <h1>Este endereço não existe</h1>
      <p>Use a navegação para retornar à visão operacional.</p>
      <Link className="primary-button" to="/processing-health">
        Ir para visão geral
      </Link>
    </section>
  );
}
