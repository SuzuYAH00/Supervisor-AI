import { useState } from "react";

import { ErrorState } from "../../../components/feedback/ErrorState";
import { LoadingState } from "../../../components/feedback/LoadingState";
import { CsvImportForm } from "../components/CsvImportForm";
import { CsvImportResult } from "../components/CsvImportResult";
import { useCsvImport } from "../hooks/use-csv-import";

function validateFile(file: File | null): string | null {
  if (file === null) return "Selecione um arquivo CSV.";
  if (!file.name.toLowerCase().endsWith(".csv")) {
    return "O arquivo selecionado deve possuir a extensão .csv.";
  }
  if (file.size === 0) return "O arquivo CSV não pode estar vazio.";
  return null;
}

export function CsvImportPage() {
  const operation = useCsvImport();
  const [file, setFile] = useState<File | null>(null);
  const [localError, setLocalError] = useState<string | null>(null);
  const [inputKey, setInputKey] = useState(0);

  const selectFile = (selectedFile: File | null) => {
    operation.reset();
    setFile(selectedFile);
    setLocalError(selectedFile === null ? null : validateFile(selectedFile));
  };

  const submit = () => {
    const validationError = validateFile(file);
    setLocalError(validationError);
    if (validationError === null && file !== null) operation.submit(file);
  };

  const newImport = () => {
    operation.reset();
    setFile(null);
    setLocalError(null);
    setInputKey((current) => current + 1);
  };

  return (
    <div className="page-stack">
      <header className="page-header">
        <div>
          <p className="eyebrow">Importação operacional</p>
          <h1>Importar arquivo CSV</h1>
          <p>
            Envie um arquivo para o pipeline existente. O conteúdo e as regras
            são validados pelo backend.
          </p>
        </div>
      </header>

      <CsvImportForm
        file={file}
        inputKey={inputKey}
        localError={localError}
        isSubmitting={operation.isSubmitting}
        onFileChange={selectFile}
        onSubmit={submit}
      />

      {operation.isSubmitting ? (
        <LoadingState
          title="Importando arquivo CSV"
          description={`Enviando e processando ${file?.name ?? "o arquivo selecionado"}.`}
        />
      ) : null}

      {!operation.isSubmitting && operation.error !== null ? (
        <ErrorState error={operation.error} onRetry={operation.retry} />
      ) : null}

      {!operation.isSubmitting &&
      operation.error === null &&
      operation.data !== null ? (
        <CsvImportResult result={operation.data} onNewImport={newImport} />
      ) : null}
    </div>
  );
}
