interface CsvImportFormProps {
  readonly file: File | null;
  readonly inputKey: number;
  readonly localError: string | null;
  readonly isSubmitting: boolean;
  readonly onFileChange: (file: File | null) => void;
  readonly onSubmit: () => void;
}

export function CsvImportForm({
  file,
  inputKey,
  localError,
  isSubmitting,
  onFileChange,
  onSubmit,
}: CsvImportFormProps) {
  return (
    <section className="financial-table-card" aria-labelledby="csv-file-title">
      <h2 id="csv-file-title">Arquivo CSV</h2>
      <form
        className="csv-import-form"
        onSubmit={(event) => {
          event.preventDefault();
          onSubmit();
        }}
      >
        <div className="form-field">
          <label htmlFor="csv-file">Selecione um arquivo CSV</label>
          <input
            key={inputKey}
            id="csv-file"
            type="file"
            accept=".csv,text/csv"
            disabled={isSubmitting}
            aria-describedby={
              localError === null ? "selected-csv-file" : "csv-file-error"
            }
            onChange={(event) =>
              onFileChange(event.currentTarget.files?.[0] ?? null)
            }
          />
          <small id="selected-csv-file">
            {file === null
              ? "Nenhum arquivo selecionado."
              : `Arquivo selecionado: ${file.name}`}
          </small>
          {localError !== null ? (
            <span id="csv-file-error" className="field-error" role="alert">
              {localError}
            </span>
          ) : null}
        </div>
        <button
          className="primary-button"
          type="submit"
          disabled={file === null || localError !== null || isSubmitting}
        >
          Importar CSV
        </button>
      </form>
    </section>
  );
}
