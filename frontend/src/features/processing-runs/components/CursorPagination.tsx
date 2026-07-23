interface CursorPaginationProps {
  sessionPage: number;
  canGoNext: boolean;
  canGoPrevious: boolean;
  onNext: () => void;
  onPrevious: () => void;
}

export function CursorPagination({
  sessionPage,
  canGoNext,
  canGoPrevious,
  onNext,
  onPrevious,
}: CursorPaginationProps) {
  return (
    <nav className="cursor-pagination" aria-label="Paginação das execuções">
      <button
        className="button button--secondary"
        type="button"
        disabled={!canGoPrevious}
        onClick={onPrevious}
      >
        Página anterior
      </button>
      <span aria-live="polite">Página {sessionPage} desta sessão</span>
      <button
        className="button button--secondary"
        type="button"
        disabled={!canGoNext}
        onClick={onNext}
      >
        Próxima página
      </button>
    </nav>
  );
}
