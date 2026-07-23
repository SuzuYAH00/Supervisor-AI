interface NotFoundAction {
  readonly label: string;
  readonly onClick: () => void;
}

interface NotFoundStateProps {
  readonly eyebrow?: string;
  readonly title: string;
  readonly description: string;
  readonly action?: NotFoundAction;
}

export function NotFoundState({
  eyebrow,
  title,
  description,
  action,
}: NotFoundStateProps) {
  return (
    <section className="feedback-state error-state" role="alert">
      {eyebrow !== undefined ? <p className="eyebrow">{eyebrow}</p> : null}
      <h2>{title}</h2>
      <p>{description}</p>
      {action !== undefined ? (
        <button className="primary-button" type="button" onClick={action.onClick}>
          {action.label}
        </button>
      ) : null}
    </section>
  );
}
