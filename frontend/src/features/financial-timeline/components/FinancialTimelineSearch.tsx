import { useState } from "react";
import type { FormEvent } from "react";

interface FinancialTimelineSearchProps {
  readonly submittedCollaboratorId: string | null;
  readonly isLoading: boolean;
  readonly onSubmit: (collaboratorId: string) => void;
}

export function FinancialTimelineSearch({
  submittedCollaboratorId,
  isLoading,
  onSubmit,
}: FinancialTimelineSearchProps) {
  const [value, setValue] = useState("");
  const [validationMessage, setValidationMessage] = useState<string | null>(
    null,
  );
  const normalizedValue = value.trim();
  const submittingCurrentValue =
    isLoading && normalizedValue === submittedCollaboratorId;

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (normalizedValue === "") {
      setValidationMessage("Informe um identificador de colaborador.");
      return;
    }
    setValidationMessage(null);
    onSubmit(normalizedValue);
  }

  return (
    <form className="timeline-search" onSubmit={submit} noValidate>
      <div className="form-field">
        <label htmlFor="collaborator-id">Identificador do colaborador</label>
        <input
          id="collaborator-id"
          name="collaborator_id"
          type="text"
          value={value}
          aria-describedby={
            validationMessage === null ? "collaborator-id-help" : "collaborator-id-error"
          }
          aria-invalid={validationMessage !== null}
          onChange={(event) => {
            setValue(event.target.value);
            if (validationMessage !== null) {
              setValidationMessage(null);
            }
          }}
        />
        <small id="collaborator-id-help">
          Use o identificador exato, preservando maiúsculas e minúsculas.
        </small>
        {validationMessage !== null && (
          <span id="collaborator-id-error" className="field-error" role="alert">
            {validationMessage}
          </span>
        )}
      </div>
      <button
        className="primary-button"
        type="submit"
        disabled={submittingCurrentValue}
      >
        Consultar timeline
      </button>
    </form>
  );
}
