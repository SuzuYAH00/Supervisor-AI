import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";

import { getCommercialEventDetail } from "../src/features/commercial-events/api/get-commercial-event-detail";
import { CommercialEventDetailPage } from "../src/features/commercial-events/pages/CommercialEventDetailPage";
import { ApiError } from "../src/lib/http/api-error";
import { commercialEventDetail } from "./fixtures";

vi.mock(
  "../src/features/commercial-events/api/get-commercial-event-detail",
  () => ({ getCommercialEventDetail: vi.fn() }),
);

const getCommercialEventDetailMock = vi.mocked(getCommercialEventDetail);

function renderDetail(path = "/commercial-events/event-1") {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route
          path="/commercial-events/:commercialEventId"
          element={<CommercialEventDetailPage />}
        />
      </Routes>
    </MemoryRouter>,
  );
}

test("confirmed not-found error keeps its specific state and retries the same ID", async () => {
  const user = userEvent.setup();
  getCommercialEventDetailMock
    .mockRejectedValueOnce(
      new ApiError({
        status: 404,
        code: "commercial_event_not_found",
        message: "Commercial event was not found",
        kind: "api",
      }),
    )
    .mockResolvedValueOnce(commercialEventDetail());
  renderDetail("/commercial-events/missing");

  expect(
    await screen.findByText("Evento comercial não encontrado"),
  ).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "Tentar novamente" }));
  expect(await screen.findByText("Evento persistido")).toBeInTheDocument();
  expect(getCommercialEventDetailMock).toHaveBeenLastCalledWith(
    "missing",
    expect.any(AbortSignal),
  );
});

test("unrecognized 404 continues through the generic ErrorState", async () => {
  getCommercialEventDetailMock.mockRejectedValue(
    new ApiError({
      status: 404,
      code: "unexpected_api_error",
      message: "O Supervisor AI não pôde concluir a solicitação.",
      kind: "api",
    }),
  );
  renderDetail();

  expect(
    await screen.findByText("A consulta não pôde ser concluída"),
  ).toBeInTheDocument();
  expect(
    screen.queryByText("Evento comercial não encontrado"),
  ).not.toBeInTheDocument();
});

test("invalid route ID is presented without executing a request", () => {
  renderDetail("/commercial-events/%20%20");
  expect(screen.getByText("Rota de evento inválida")).toBeInTheDocument();
  expect(getCommercialEventDetailMock).not.toHaveBeenCalled();
});
