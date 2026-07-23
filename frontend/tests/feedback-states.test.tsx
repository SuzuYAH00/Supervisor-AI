import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { EmptyState } from "../src/components/feedback/EmptyState";
import { InvalidRouteState } from "../src/components/feedback/InvalidRouteState";
import { NotFoundState } from "../src/components/feedback/NotFoundState";

test("not-found state presents only the content and action provided by its page", async () => {
  const user = userEvent.setup();
  const onAction = vi.fn();
  render(
    <NotFoundState
      eyebrow="Recurso ausente"
      title="O recurso não foi localizado"
      description="Descrição específica."
      action={{ label: "Consultar novamente", onClick: onAction }}
    />,
  );

  expect(screen.getByRole("alert")).toBeInTheDocument();
  await user.click(
    screen.getByRole("button", { name: "Consultar novamente" }),
  );
  expect(onAction).toHaveBeenCalledOnce();
});

test("invalid-route and empty states preserve their semantic roles", () => {
  const view = render(
    <InvalidRouteState title="Rota inválida" description="ID ausente." />,
  );
  expect(screen.getByRole("alert")).toHaveTextContent("Rota inválida");

  view.rerender(
    <EmptyState title="Sem registros" description="Consulta concluída." />,
  );
  expect(screen.getByRole("status")).toHaveTextContent("Sem registros");
});
