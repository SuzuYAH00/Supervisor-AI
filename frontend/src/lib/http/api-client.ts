import { environment } from "../config/environment";
import { ApiError } from "./api-error";

type JsonObject = { readonly [key: string]: unknown };

export type JsonParser<T> = (value: unknown) => T;

export interface ApiRequestOptions<T> {
  readonly signal?: AbortSignal;
  readonly parse: JsonParser<T>;
}

function composeUrl(path: string): string {
  const baseUrl = environment.apiBaseUrl.replace(/\/+$/, "");
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return `${baseUrl}${normalizedPath}`;
}

function isObject(value: unknown): value is JsonObject {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function apiErrorFromPayload(status: number, payload: unknown): ApiError | null {
  if (!isObject(payload) || !isObject(payload.error)) {
    return null;
  }
  const { code, message } = payload.error;
  if (typeof code !== "string" || typeof message !== "string") {
    return null;
  }
  return new ApiError({ status, code, message, kind: "api" });
}

async function readJson(response: Response): Promise<unknown> {
  try {
    return await response.json();
  } catch {
    throw new ApiError({
      status: response.status,
      code: "invalid_response",
      message: "A resposta do servidor não pôde ser interpretada.",
      kind: "invalid-response",
    });
  }
}

export async function apiRequest<T>(
  path: string,
  options: ApiRequestOptions<T>,
): Promise<T> {
  let response: Response;
  try {
    response = await fetch(composeUrl(path), {
      headers: { Accept: "application/json" },
      signal: options.signal,
    });
  } catch (error: unknown) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new ApiError({
        code: "request_cancelled",
        message: "A requisição foi cancelada.",
        kind: "cancelled",
      });
    }
    throw new ApiError({
      code: "network_error",
      message: "Não foi possível conectar ao Supervisor AI.",
      kind: "network",
    });
  }

  const payload = await readJson(response);
  if (!response.ok) {
    const knownError = apiErrorFromPayload(response.status, payload);
    if (knownError !== null) {
      throw knownError;
    }
    throw new ApiError({
      status: response.status,
      code: "unexpected_api_error",
      message: "O Supervisor AI não pôde concluir a solicitação.",
      kind: "invalid-response",
    });
  }

  try {
    return options.parse(payload);
  } catch (error: unknown) {
    if (error instanceof ApiError) {
      throw error;
    }
    throw new ApiError({
      status: response.status,
      code: "invalid_response",
      message: "A resposta do servidor não possui o formato esperado.",
      kind: "invalid-response",
    });
  }
}
