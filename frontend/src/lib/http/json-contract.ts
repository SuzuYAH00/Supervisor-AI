export type JsonObject = { readonly [key: string]: unknown };

export function jsonObject(value: unknown, field: string): JsonObject {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new TypeError(`Invalid ${field}`);
  }
  const result: Record<string, unknown> = {};
  for (const [key, item] of Object.entries(value)) {
    result[key] = item;
  }
  return result;
}

export function nullableText(value: unknown, field: string): string | null {
  if (value === null || typeof value === "string") {
    return value;
  }
  throw new TypeError(`Invalid ${field}`);
}

export function text(value: unknown, field: string): string {
  if (typeof value === "string") {
    return value;
  }
  throw new TypeError(`Invalid ${field}`);
}

export function nonNegativeInteger(value: unknown, field: string): number {
  if (typeof value === "number" && Number.isInteger(value) && value >= 0) {
    return value;
  }
  throw new TypeError(`Invalid ${field}`);
}

export function jsonList<T>(
  value: unknown,
  parseItem: (item: unknown) => T,
  field: string,
): readonly T[] {
  if (!Array.isArray(value)) {
    throw new TypeError(`Invalid ${field}`);
  }
  return value.map(parseItem);
}
