type ApiErrorKind = "api" | "network" | "invalid-response" | "cancelled";

export class ApiError extends Error {
  readonly status: number | null;
  readonly code: string;
  readonly kind: ApiErrorKind;

  constructor(options: {
    message: string;
    code: string;
    kind: ApiErrorKind;
    status?: number | null;
  }) {
    super(options.message);
    this.name = "ApiError";
    this.status = options.status ?? null;
    this.code = options.code;
    this.kind = options.kind;
  }
}
