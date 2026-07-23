interface MetricCardProps {
  readonly label: string;
  readonly value: number;
  readonly description: string;
}

export function MetricCard({ label, value, description }: MetricCardProps) {
  return (
    <article className="metric-card">
      <p>{label}</p>
      <strong>{value.toLocaleString("pt-BR")}</strong>
      <small>{description}</small>
    </article>
  );
}
