interface EmptyStateProps {
  readonly title: string;
  readonly description: string;
}

export function EmptyState({ title, description }: EmptyStateProps) {
  return (
    <section className="empty-banner" role="status">
      <strong>{title}</strong>
      <span>{description}</span>
    </section>
  );
}
