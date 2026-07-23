interface DistributionItem {
  readonly key: string;
  readonly label: string;
  readonly count: number;
}

interface DistributionListProps {
  readonly title: string;
  readonly description: string;
  readonly items: readonly DistributionItem[];
}

export function DistributionList({
  title,
  description,
  items,
}: DistributionListProps) {
  const orderedItems = [...items].sort((left, right) =>
    left.label.localeCompare(right.label, "pt-BR"),
  );

  return (
    <section className="distribution-card">
      <header>
        <h2>{title}</h2>
        <p>{description}</p>
      </header>
      {orderedItems.length === 0 ? (
        <p className="empty-list">Nenhum registro nesta distribuição.</p>
      ) : (
        <ul>
          {orderedItems.map((item) => (
            <li key={item.key}>
              <span>{item.label}</span>
              <strong>{item.count.toLocaleString("pt-BR")}</strong>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
