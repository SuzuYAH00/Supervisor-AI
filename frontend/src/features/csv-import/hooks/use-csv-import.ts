import { useCallback, useEffect, useRef, useState } from "react";

import { ApiError } from "../../../lib/http/api-error";
import { importCsv } from "../api/import-csv";
import type { CsvImportResult } from "../types/csv-import";

interface CsvImportState {
  readonly data: CsvImportResult | null;
  readonly error: ApiError | null;
  readonly isSubmitting: boolean;
  readonly submit: (file: File) => void;
  readonly retry: () => void;
  readonly reset: () => void;
}

export function useCsvImport(): CsvImportState {
  const [data, setData] = useState<CsvImportResult | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const controllerRef = useRef<AbortController | null>(null);
  const requestVersionRef = useRef(0);
  const retryFileRef = useRef<File | null>(null);
  const mountedRef = useRef(true);

  useEffect(
    () => () => {
      mountedRef.current = false;
      controllerRef.current?.abort();
    },
    [],
  );

  const submit = useCallback((file: File) => {
    controllerRef.current?.abort();
    const controller = new AbortController();
    controllerRef.current = controller;
    retryFileRef.current = file;
    const requestVersion = ++requestVersionRef.current;
    setData(null);
    setError(null);
    setIsSubmitting(true);

    void importCsv(file, controller.signal)
      .then((result) => {
        if (
          mountedRef.current &&
          requestVersionRef.current === requestVersion
        ) {
          setData(result);
        }
      })
      .catch((cause: unknown) => {
        if (
          !mountedRef.current ||
          requestVersionRef.current !== requestVersion ||
          (cause instanceof ApiError && cause.kind === "cancelled")
        ) {
          return;
        }
        setError(
          cause instanceof ApiError
            ? cause
            : new ApiError({
                code: "unexpected_error",
                message: "Não foi possível importar o arquivo CSV.",
                kind: "invalid-response",
              }),
        );
      })
      .finally(() => {
        if (
          mountedRef.current &&
          requestVersionRef.current === requestVersion
        ) {
          setIsSubmitting(false);
        }
      });
  }, []);

  const retry = useCallback(() => {
    if (retryFileRef.current !== null) submit(retryFileRef.current);
  }, [submit]);

  const reset = useCallback(() => {
    controllerRef.current?.abort();
    requestVersionRef.current += 1;
    retryFileRef.current = null;
    setData(null);
    setError(null);
    setIsSubmitting(false);
  }, []);

  return { data, error, isSubmitting, submit, retry, reset };
}
