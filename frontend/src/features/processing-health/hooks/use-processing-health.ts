import { useCallback, useEffect, useState } from "react";

import { ApiError } from "../../../lib/http/api-error";
import { getProcessingHealth } from "../api/get-processing-health";
import type { ProcessingHealth } from "../types/processing-health";

interface ProcessingHealthState {
  readonly data: ProcessingHealth | null;
  readonly error: ApiError | null;
  readonly isLoading: boolean;
  readonly refetch: () => void;
}

export function useProcessingHealth(): ProcessingHealthState {
  const [data, setData] = useState<ProcessingHealth | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [requestVersion, setRequestVersion] = useState(0);

  const refetch = useCallback(() => {
    setRequestVersion((current) => current + 1);
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    let active = true;
    setIsLoading(true);
    setError(null);

    void getProcessingHealth({}, controller.signal)
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
                message: "Não foi possível carregar os dados de processamento.",
                kind: "invalid-response",
              }),
        );
        setIsLoading(false);
      });

    return () => {
      active = false;
      controller.abort();
    };
  }, [requestVersion]);

  return { data, error, isLoading, refetch };
}
