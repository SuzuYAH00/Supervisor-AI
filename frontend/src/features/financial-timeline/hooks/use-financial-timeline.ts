import { useCallback, useEffect, useState } from "react";

import { ApiError } from "../../../lib/http/api-error";
import { getFinancialTimeline } from "../api/get-financial-timeline";
import type { FinancialTimeline } from "../types/financial-timeline";

interface FinancialTimelineState {
  readonly data: FinancialTimeline | null;
  readonly error: ApiError | null;
  readonly isLoading: boolean;
  readonly hasSearched: boolean;
  readonly submittedCollaboratorId: string | null;
  readonly sessionPage: number;
  readonly canGoNext: boolean;
  readonly canGoPrevious: boolean;
  readonly submitCollaborator: (collaboratorId: string) => void;
  readonly goNext: () => void;
  readonly goPrevious: () => void;
  readonly refetch: () => void;
}

export function useFinancialTimeline(): FinancialTimelineState {
  const [data, setData] = useState<FinancialTimeline | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [submittedCollaboratorId, setSubmittedCollaboratorId] = useState<
    string | null
  >(null);
  const [cursorHistory, setCursorHistory] = useState<
    readonly (string | undefined)[]
  >([undefined]);
  const [requestVersion, setRequestVersion] = useState(0);
  const currentCursor = cursorHistory[cursorHistory.length - 1];

  const startTransition = useCallback(() => {
    setData(null);
    setError(null);
    setIsLoading(true);
  }, []);

  const submitCollaborator = useCallback(
    (collaboratorId: string) => {
      startTransition();
      setSubmittedCollaboratorId(collaboratorId);
      setCursorHistory([undefined]);
      setRequestVersion((current) => current + 1);
    },
    [startTransition],
  );

  const refetch = useCallback(() => {
    if (submittedCollaboratorId === null) {
      return;
    }
    startTransition();
    setRequestVersion((current) => current + 1);
  }, [startTransition, submittedCollaboratorId]);

  const goNext = useCallback(() => {
    const nextCursor = data?.page.next_cursor;
    if (
      data?.page.has_more !== true ||
      nextCursor === null ||
      nextCursor === undefined ||
      isLoading
    ) {
      return;
    }
    startTransition();
    setCursorHistory((current) => [...current, nextCursor]);
  }, [data, isLoading, startTransition]);

  const goPrevious = useCallback(() => {
    if (cursorHistory.length <= 1 || isLoading) {
      return;
    }
    startTransition();
    setCursorHistory((current) => current.slice(0, -1));
  }, [cursorHistory.length, isLoading, startTransition]);

  useEffect(() => {
    if (submittedCollaboratorId === null) {
      return;
    }
    const controller = new AbortController();
    let active = true;
    setIsLoading(true);
    setError(null);

    void getFinancialTimeline(
      submittedCollaboratorId,
      currentCursor === undefined ? {} : { cursor: currentCursor },
      controller.signal,
    )
      .then((result) => {
        if (!active) {
          return;
        }
        setData(result);
        setIsLoading(false);
      })
      .catch((cause: unknown) => {
        if (
          !active ||
          (cause instanceof ApiError && cause.kind === "cancelled")
        ) {
          return;
        }
        setData(null);
        setError(
          cause instanceof ApiError
            ? cause
            : new ApiError({
                code: "unexpected_error",
                message: "Não foi possível carregar a timeline financeira.",
                kind: "invalid-response",
              }),
        );
        setIsLoading(false);
      });

    return () => {
      active = false;
      controller.abort();
    };
  }, [currentCursor, requestVersion, submittedCollaboratorId]);

  return {
    data,
    error,
    isLoading,
    hasSearched: submittedCollaboratorId !== null,
    submittedCollaboratorId,
    sessionPage: cursorHistory.length,
    canGoNext:
      !isLoading &&
      data !== null &&
      data.page.has_more &&
      data.page.next_cursor !== null,
    canGoPrevious: !isLoading && cursorHistory.length > 1,
    submitCollaborator,
    goNext,
    goPrevious,
    refetch,
  };
}
