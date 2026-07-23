interface CursorPaginationProps {
  readonly sessionPage: number;
  readonly canGoNext: boolean;
  readonly canGoPrevious: boolean;
  readonly onNext: () => void;
  readonly onPrevious: () => void;
}

export function CursorPagination({
  sessionPage,
  canGoNext,
  canGoPrevious,
  onNext,
  onPrevious,
}: CursorPaginationProps) {
  return (
    <nav className="pagination-controls" aria-label="Paginação da timeline">
      <button
        className="secondary-button"
        type="button"
        disabled={!canGoPrevious}
        onClick={onPrevious}
      >
        Página anterior
      </button>
      <span aria-live="polite">Página {sessionPage} desta consulta</span>
      <button
        className="secondary-button"
        type="button"
        disabled={!canGoNext}
        onClick={onNext}
      >
        Próxima página
      </button>
    </nav>
  );
}
