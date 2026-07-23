import { useCallback, useEffect, useState } from "react";

import { ApiError } from "../../../lib/http/api-error";
import { getProcessingRuns } from "../api/get-processing-runs";
import type { ProcessingRunsResponse } from "../types/processing-runs";

interface ProcessingRunsState {
  readonly data: ProcessingRunsResponse | null;
  readonly error: ApiError | null;
  readonly isLoading: boolean;
  readonly sessionPage: number;
  readonly canGoNext: boolean;
  readonly canGoPrevious: boolean;
  readonly goNext: () => void;
  readonly goPrevious: () => void;
  readonly refetch: () => void;
}

export function useProcessingRuns(): ProcessingRunsState {
  const [data, setData] = useState<ProcessingRunsResponse | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [cursorHistory, setCursorHistory] = useState<(string | undefined)[]>([
    undefined,
  ]);
  const [requestVersion, setRequestVersion] = useState(0);
  const currentCursor = cursorHistory.at(-1);

  useEffect(() => {
    const controller = new AbortController();
    let active = true;

    setIsLoading(true);
    setData(null);
    setError(null);

    getProcessingRuns(
      currentCursor === undefined ? {} : { cursor: currentCursor },
      controller.signal,
    )
      .then((response) => {
        if (active) setData(response);
      })
      .catch((requestError: unknown) => {
        if (active && !controller.signal.aborted) {
          setError(
            requestError instanceof ApiError
              ? requestError
              : new ApiError({
                  code: "unexpected_error",
                  message:
                    "Não foi possível carregar as execuções de processamento.",
                  kind: "invalid-response",
                }),
          );
        }
      })
      .finally(() => {
        if (active) setIsLoading(false);
      });

    return () => {
      active = false;
      controller.abort();
    };
  }, [currentCursor, requestVersion]);

  const goNext = useCallback(() => {
    const nextCursor = data?.next_cursor;
    if (isLoading || nextCursor === null || nextCursor === undefined) return;
    setCursorHistory((history) => [...history, nextCursor]);
  }, [data, isLoading]);

  const goPrevious = useCallback(() => {
    if (isLoading) return;
    setCursorHistory((history) =>
      history.length > 1 ? history.slice(0, -1) : history,
    );
  }, [isLoading]);

  const refetch = useCallback(() => {
    setRequestVersion((version) => version + 1);
  }, []);

  return {
    data,
    error,
    isLoading,
    sessionPage: cursorHistory.length,
    canGoNext: !isLoading && data !== null && data.next_cursor !== null,
    canGoPrevious: !isLoading && cursorHistory.length > 1,
    goNext,
    goPrevious,
    refetch,
  };
}
