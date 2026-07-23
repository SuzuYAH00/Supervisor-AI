import { ApiError } from "../src/lib/http/api-error";
import { apiRequest } from "../src/lib/http/api-client";

const parseMessage = (value: unknown): string => {
  if (
    typeof value === "object" &&
    value !== null &&
    "message" in value &&
    typeof value.message === "string"
  ) {
    return value.message;
  }
  throw new TypeError("invalid payload");
};

function response(body: string, status = 200, contentType = "application/json") {
  return new Response(body, {
    status,
    headers: { "Content-Type": contentType },
  });
}

test("returns parsed payload and composes the configured URL", async () => {
  const fetchMock = vi
    .fn<typeof fetch>()
    .mockResolvedValue(response('{"message":"ok"}'));
  vi.stubGlobal("fetch", fetchMock);

  await expect(
    apiRequest("/processing/health?source=csv", { parse: parseMessage }),
  ).resolves.toBe("ok");
  expect(fetchMock).toHaveBeenCalledWith(
    "/api/processing/health?source=csv",
    expect.objectContaining({ signal: undefined }),
  );
});

test("maps a known API error envelope", async () => {
  vi.stubGlobal(
    "fetch",
    vi
      .fn<typeof fetch>()
      .mockResolvedValue(
        response(
          '{"error":{"code":"invalid_query_parameters","message":"Invalid"}}',
          422,
        ),
      ),
  );

  await expect(
    apiRequest("/processing/health", { parse: parseMessage }),
  ).rejects.toMatchObject({
    status: 422,
    code: "invalid_query_parameters",
    message: "Invalid",
    kind: "api",
  });
});

test("maps non-JSON responses to a safe error", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn<typeof fetch>().mockResolvedValue(response("<html>error</html>", 500)),
  );
  await expect(
    apiRequest("/processing/health", { parse: parseMessage }),
  ).rejects.toMatchObject({
    code: "invalid_response",
    kind: "invalid-response",
  });
});

test("maps network failures without exposing the original error", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn<typeof fetch>().mockRejectedValue(new Error("internal host leaked")),
  );
  await expect(
    apiRequest("/processing/health", { parse: parseMessage }),
  ).rejects.toEqual(
    expect.objectContaining({
      code: "network_error",
      message: "Não foi possível conectar ao Supervisor AI.",
    }),
  );
});

test("supports AbortSignal and classifies cancellation", async () => {
  const controller = new AbortController();
  const fetchMock = vi.fn<typeof fetch>().mockImplementation((_input, init) => {
    return new Promise((_resolve, reject) => {
      init?.signal?.addEventListener("abort", () => {
        reject(new DOMException("aborted", "AbortError"));
      });
    });
  });
  vi.stubGlobal("fetch", fetchMock);

  const pending = apiRequest("/processing/health", {
    parse: parseMessage,
    signal: controller.signal,
  });
  controller.abort();
  await expect(pending).rejects.toMatchObject({
    code: "request_cancelled",
    kind: "cancelled",
  });
});

test("invalid successful payload is rejected safely", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn<typeof fetch>().mockResolvedValue(response('{"unexpected":true}')),
  );
  await expect(
    apiRequest("/processing/health", { parse: parseMessage }),
  ).rejects.toBeInstanceOf(ApiError);
});
