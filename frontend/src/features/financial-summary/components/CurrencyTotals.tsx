import type { CurrencyTotal } from "../types/financial-summary";

interface CurrencyTotalsProps {
  readonly totals: readonly CurrencyTotal[];
}

export function CurrencyTotals({ totals }: CurrencyTotalsProps) {
  const orderedTotals = [...totals].sort((left, right) =>
    left.currency.localeCompare(right.currency),
  );

  return (
    <section className="distribution-card" aria-labelledby="currency-totals">
      <header>
        <h2 id="currency-totals">Totais por moeda</h2>
        <p>Valores são exibidos como recebidos da API, sem conversão monetária.</p>
      </header>
      {orderedTotals.length === 0 ? (
        <p className="empty-list">Nenhum valor financeiro disponível.</p>
      ) : (
        <ul>
          {orderedTotals.map((total) => (
            <li key={total.currency}>
              <span>{total.currency}</span>
              <strong>
                {total.currency} {total.amount}
              </strong>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
