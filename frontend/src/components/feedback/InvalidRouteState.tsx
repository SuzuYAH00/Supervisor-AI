interface InvalidRouteStateProps {
  readonly title: string;
  readonly description: string;
}

export function InvalidRouteState({
  title,
  description,
}: InvalidRouteStateProps) {
  return (
    <section className="feedback-state error-state" role="alert">
      <h2>{title}</h2>
      <p>{description}</p>
    </section>
  );
}
