import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { getCommercialEvents } from "../src/features/commercial-events/api/get-commercial-events";
import { CommercialEventsPage } from "../src/features/commercial-events/pages/CommercialEventsPage";
import { ApiError } from "../src/lib/http/api-error";
import { commercialEvents } from "./fixtures";

vi.mock(
  "../src/features/commercial-events/api/get-commercial-events",
  () => ({ getCommercialEvents: vi.fn() }),
);

const getCommercialEventsMock = vi.mocked(getCommercialEvents);

test("announces loading and renders factual event fields", async () => {
  let resolveRequest: (value: ReturnType<typeof commercialEvents>) => void =
    () => undefined;
  getCommercialEventsMock.mockReturnValue(
    new Promise((resolve) => {
      resolveRequest = resolve;
    }),
  );
  render(<CommercialEventsPage />);
  expect(screen.getByText("Carregando eventos comerciais")).toBeInTheDocument();

  resolveRequest(commercialEvents());
  expect(await screen.findByText("Eventos persistidos")).toBeInTheDocument();
  const eventRow = screen.getByRole("row", {
    name: /event-2 external-2 csv-example/,
  });
  expect(within(eventRow).getByText("2026-07-22T12:00:00Z")).toHaveAttribute(
    "datetime",
    "2026-07-22T12:00:00Z",
  );
  expect(screen.queryByText(/comissão/i)).not.toBeInTheDocument();
  expect(screen.queryByText(/status/i)).not.toBeInTheDocument();
});

test("renders an empty result as success with next disabled", async () => {
  getCommercialEventsMock.mockResolvedValue(
    commercialEvents({ items: [] }),
  );
  render(<CommercialEventsPage />);

  expect(
    await screen.findByText("Nenhum evento comercial foi encontrado."),
  ).toBeInTheDocument();
  expect(
    screen.getByRole("button", { name: "Próxima página" }),
  ).toBeDisabled();
  expect(screen.getByText("Página 1 desta sessão")).toBeInTheDocument();
});

test("retries an initial error", async () => {
  const user = userEvent.setup();
  getCommercialEventsMock
    .mockRejectedValueOnce(
      new ApiError({
        code: "network_error",
        message: "Não foi possível conectar ao Supervisor AI.",
        kind: "network",
      }),
    )
    .mockResolvedValueOnce(commercialEvents());
  render(<CommercialEventsPage />);

  expect(await screen.findByText("O backend está indisponível")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Tentar novamente" }));
  expect(await screen.findByText("Eventos persistidos")).toBeInTheDocument();
  expect(getCommercialEventsMock).toHaveBeenLastCalledWith(
    {},
    expect.any(AbortSignal),
  );
});

test("navigates forward and backward using opaque cursor history", async () => {
  const user = userEvent.setup();
  let resolveSecondPage: (value: ReturnType<typeof commercialEvents>) => void =
    () => undefined;
  getCommercialEventsMock
    .mockResolvedValueOnce(
      commercialEvents({
        page: { limit: 1, next_cursor: "cursor-page-2", has_more: true },
      }),
    )
    .mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          resolveSecondPage = resolve;
        }),
    )
    .mockResolvedValueOnce(
      commercialEvents({
        page: { limit: 1, next_cursor: "cursor-page-2", has_more: true },
      }),
    );
  render(<CommercialEventsPage />);

  const nextButton = await screen.findByRole("button", {
    name: "Próxima página",
  });
  expect(nextButton).toBeEnabled();
  await user.click(nextButton);
  expect(screen.getByText("Carregando eventos comerciais")).toBeInTheDocument();
  resolveSecondPage(
    commercialEvents({
      page: { limit: 1, next_cursor: null, has_more: false },
      items: [
        {
          event_id: "event-1",
          external_reference: "external-1",
          source: "csv-example",
          occurred_at: "2026-07-21T12:00:00Z",
          received_at: "2026-07-21T12:01:00Z",
          created_at: "2026-07-21T12:01:00Z",
        },
      ],
    }),
  );
  expect(await screen.findByText("event-1")).toBeInTheDocument();
  expect(screen.getByText("Página 2 desta sessão")).toBeInTheDocument();
  expect(
    screen.getByRole("button", { name: "Próxima página" }),
  ).toBeDisabled();
  expect(getCommercialEventsMock).toHaveBeenNthCalledWith(
    2,
    { cursor: "cursor-page-2" },
    expect.any(AbortSignal),
  );

  await user.click(screen.getByRole("button", { name: "Página anterior" }));
  expect(await screen.findByText("event-2")).toBeInTheDocument();
  expect(screen.getByText("Página 1 desta sessão")).toBeInTheDocument();
  expect(getCommercialEventsMock).toHaveBeenNthCalledWith(
    3,
    {},
    expect.any(AbortSignal),
  );
});

test("retry after a page transition repeats the requested cursor", async () => {
  const user = userEvent.setup();
  getCommercialEventsMock
    .mockResolvedValueOnce(
      commercialEvents({
        page: { limit: 1, next_cursor: "failed-page", has_more: true },
      }),
    )
    .mockRejectedValueOnce(
      new ApiError({
        code: "network_error",
        message: "Não foi possível conectar ao Supervisor AI.",
        kind: "network",
      }),
    )
    .mockResolvedValueOnce(commercialEvents());
  render(<CommercialEventsPage />);

  await user.click(
    await screen.findByRole("button", { name: "Próxima página" }),
  );
  expect(await screen.findByText("O backend está indisponível")).toBeInTheDocument();
  expect(screen.queryByText("event-2")).not.toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Tentar novamente" }));
  await waitFor(() => expect(getCommercialEventsMock).toHaveBeenCalledTimes(3));
  expect(getCommercialEventsMock).toHaveBeenLastCalledWith(
    { cursor: "failed-page" },
    expect.any(AbortSignal),
  );
});

test("aborts the active request when unmounted", () => {
  let receivedSignal: AbortSignal | undefined;
  getCommercialEventsMock.mockImplementation((_query, signal) => {
    receivedSignal = signal;
    return new Promise(() => undefined);
  });
  const view = render(<CommercialEventsPage />);
  expect(receivedSignal?.aborted).toBe(false);
  view.unmount();
  expect(receivedSignal?.aborted).toBe(true);
});
