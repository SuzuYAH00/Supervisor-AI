interface CursorPaginationProps {
  readonly sessionPage: number;
  readonly canGoNext: boolean;
  readonly canGoPrevious: boolean;
  readonly isLoading: boolean;
  readonly onNext: () => void;
  readonly onPrevious: () => void;
}

export function CursorPagination({
  sessionPage,
  canGoNext,
  canGoPrevious,
  isLoading,
  onNext,
  onPrevious,
}: CursorPaginationProps) {
  return (
    <nav className="pagination-controls" aria-label="Paginação dos eventos">
      <button
        className="secondary-button"
        type="button"
        disabled={!canGoPrevious}
        onClick={onPrevious}
      >
        Página anterior
      </button>
      <span aria-live="polite">Página {sessionPage} desta sessão</span>
      <button
        className="secondary-button"
        type="button"
        disabled={!canGoNext}
        onClick={onNext}
      >
        {isLoading ? "Carregando" : "Próxima página"}
      </button>
    </nav>
  );
}
