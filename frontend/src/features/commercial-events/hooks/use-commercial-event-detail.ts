import { useCallback, useEffect, useState } from "react";

import { ApiError } from "../../../lib/http/api-error";
import { getCommercialEventDetail } from "../api/get-commercial-event-detail";
import type { CommercialEventDetailResponse } from "../types/commercial-event-detail";

interface CommercialEventDetailState {
  readonly data: CommercialEventDetailResponse | null;
  readonly error: ApiError | null;
  readonly isLoading: boolean;
  readonly isInvalidId: boolean;
  readonly refetch: () => void;
}

export function useCommercialEventDetail(
  eventId: string | undefined,
): CommercialEventDetailState {
  const [data, setData] = useState<CommercialEventDetailResponse | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [requestVersion, setRequestVersion] = useState(0);
  const isInvalidId = eventId === undefined || eventId.trim() === "";

  const refetch = useCallback(() => {
    if (!isInvalidId) setRequestVersion((current) => current + 1);
  }, [isInvalidId]);

  useEffect(() => {
    setData(null);
    setError(null);
    if (eventId === undefined || eventId.trim() === "") {
      setIsLoading(false);
      return;
    }

    const controller = new AbortController();
    let active = true;
    setIsLoading(true);
    void getCommercialEventDetail(eventId, controller.signal)
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
                message: "Não foi possível carregar os detalhes do evento.",
                kind: "invalid-response",
              }),
        );
        setIsLoading(false);
      });

    return () => {
      active = false;
      controller.abort();
    };
  }, [eventId, requestVersion]);

  return { data, error, isLoading, isInvalidId, refetch };
}
