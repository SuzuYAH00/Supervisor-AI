import { useCallback, useEffect, useState } from "react";

import { ApiError } from "../../../lib/http/api-error";
import { getProcessingRunDetail } from "../api/get-processing-run-detail";
import type { ProcessingRunDetailResponse } from "../types/processing-run-detail";

interface ProcessingRunDetailState {
  readonly data: ProcessingRunDetailResponse | null;
  readonly error: ApiError | null;
  readonly isLoading: boolean;
  readonly isInvalidId: boolean;
  readonly refetch: () => void;
}

export function useProcessingRunDetail(
  processingRunId: string | undefined,
): ProcessingRunDetailState {
  const [data, setData] = useState<ProcessingRunDetailResponse | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [requestVersion, setRequestVersion] = useState(0);
  const isInvalidId =
    processingRunId === undefined || processingRunId.trim() === "";

  const refetch = useCallback(() => {
    if (!isInvalidId) {
      setRequestVersion((current) => current + 1);
    }
  }, [isInvalidId]);

  useEffect(() => {
    setData(null);
    setError(null);
    if (processingRunId === undefined || processingRunId.trim() === "") {
      setIsLoading(false);
      return;
    }

    const controller = new AbortController();
    let active = true;
    setIsLoading(true);

    void getProcessingRunDetail(processingRunId, controller.signal)
      .then((result) => {
        if (!active) return;
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
        setError(
          cause instanceof ApiError
            ? cause
            : new ApiError({
                code: "unexpected_error",
                message: "Não foi possível carregar os detalhes da execução.",
                kind: "invalid-response",
              }),
        );
        setIsLoading(false);
      });

    return () => {
      active = false;
      controller.abort();
    };
  }, [processingRunId, requestVersion]);

  return {
    data,
    error,
    isLoading,
    isInvalidId,
    refetch,
  };
}
