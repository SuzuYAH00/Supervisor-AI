import { Link, NavLink, Outlet } from "react-router-dom";

const futureNavigation = ["Execuções", "Timeline"];

export function AppLayout() {
  return (
    <div className="app-shell">
      <header className="topbar">
        <div>
          <Link
            className="brand"
            to="/processing-health"
            aria-label="Supervisor AI"
          >
            Supervisor <span>AI</span>
          </Link>
          <p>Inteligência operacional</p>
        </div>
        <span className="environment-badge">MVP interno</span>
      </header>

      <div className="app-body">
        <aside className="sidebar" aria-label="Navegação principal">
          <nav>
            <NavLink
              className={({ isActive }) =>
                `navigation-link${isActive ? " active" : ""}`
              }
              to="/processing-health"
            >
              <span>Visão geral</span>
              <small>Processamento</small>
            </NavLink>
            <NavLink
              className={({ isActive }) =>
                `navigation-link${isActive ? " active" : ""}`
              }
              to="/financial-summary"
            >
              <span>Resumo Financeiro</span>
              <small>Ledger</small>
            </NavLink>
            <NavLink
              className={({ isActive }) =>
                `navigation-link${isActive ? " active" : ""}`
              }
              to="/commercial-events"
            >
              <span>Eventos comerciais</span>
              <small>Auditoria</small>
            </NavLink>
            {futureNavigation.map((label) => (
              <span className="navigation-link disabled" key={label}>
                <span>{label}</span>
                <small>Em breve</small>
              </span>
            ))}
          </nav>
        </aside>
        <main className="main-content" id="main-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
