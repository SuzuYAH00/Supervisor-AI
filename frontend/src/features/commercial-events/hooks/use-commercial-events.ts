import { useCallback, useEffect, useState } from "react";

import { ApiError } from "../../../lib/http/api-error";
import { getCommercialEvents } from "../api/get-commercial-events";
import type { CommercialEventList } from "../types/commercial-events";

interface CommercialEventsState {
  readonly data: CommercialEventList | null;
  readonly error: ApiError | null;
  readonly isLoading: boolean;
  readonly sessionPage: number;
  readonly canGoNext: boolean;
  readonly canGoPrevious: boolean;
  readonly goNext: () => void;
  readonly goPrevious: () => void;
  readonly refetch: () => void;
}

export function useCommercialEvents(): CommercialEventsState {
  const [data, setData] = useState<CommercialEventList | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [isLoading, setIsLoading] = useState(true);
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

  const refetch = useCallback(() => {
    startTransition();
    setRequestVersion((current) => current + 1);
  }, [startTransition]);

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
    const controller = new AbortController();
    let active = true;
    setIsLoading(true);
    setError(null);

    void getCommercialEvents(
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
                message: "Não foi possível carregar os eventos comerciais.",
                kind: "invalid-response",
              }),
        );
        setIsLoading(false);
      });

    return () => {
      active = false;
      controller.abort();
    };
  }, [currentCursor, requestVersion]);

  return {
    data,
    error,
    isLoading,
    sessionPage: cursorHistory.length,
    canGoNext:
      !isLoading &&
      data !== null &&
      data.page.has_more &&
      data.page.next_cursor !== null,
    canGoPrevious: !isLoading && cursorHistory.length > 1,
    goNext,
    goPrevious,
    refetch,
  };
}
