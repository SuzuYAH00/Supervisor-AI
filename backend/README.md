# Backend do Supervisor AI

Aplicação FastAPI responsável pela API e pela infraestrutura dos motores de
importação, processamento e regras do Supervisor AI. Nesta etapa, somente a
fundação técnica da aplicação está implementada.

## Pré-requisitos

- Python 3.12;
- uv;
- Docker com Docker Compose.

Os comandos abaixo devem ser executados a partir da raiz do repositório.

## Instalação

```bash
cp .env.example .env
uv --project backend sync --all-groups
docker compose up -d postgres
```

## Migrações

```bash
uv --project backend run alembic -c backend/alembic.ini upgrade head
```

## API

```bash
SUPERVISOR_AI_DATABASE_URL="$DATABASE_URL" \
  uv --project backend run uvicorn \
  supervisor_ai.main:create_application_from_environment --factory --reload
```

A API ficará disponível em `http://localhost:8000`. O endpoint de saúde está
disponível em `http://localhost:8000/health`. A importação CSV está disponível
em `POST /imports/csv` com o arquivo no campo multipart `file`.

```bash
curl -X POST \
  -F "file=@docs/exemplos/importacao_comercial.csv;type=text/csv" \
  http://127.0.0.1:8000/imports/csv
```

A aplicação não cria tabelas ou aplica migrations durante a inicialização.

## Consulta financeira

```bash
curl \
  "http://127.0.0.1:8000/financial/snapshot?collaborator_id=collaborator-1&start_date=2026-07-01&end_date=2026-07-31"
```

Todos os filtros são opcionais. Datas são inclusivas sobre `posted_at` em UTC e
valores monetários são strings decimais. Ausência de créditos retorna HTTP 200.

O resumo gerencial dos créditos está disponível em:

```bash
curl \
  "http://127.0.0.1:8000/financial/summary?start_date=2026-07-01&end_date=2026-07-31"
```

Ele agrupa colaboradores e moedas, calcula ranking e participação com
`Decimal`, e preserva a mesma política de filtros e resposta vazia do snapshot.

O fluxo de auditoria parte do resumo, passa pelos itens do snapshot e usa o
identificador do evento:

```bash
curl \
  "http://127.0.0.1:8000/commercial-events/event-csv-1"
```

O endpoint retorna evento, LedgerEntries e ProcessingRuns em ordem
determinística. Ele é somente leitura e não expõe o `raw_payload`.

Para localizar eventos antes do drill-down, inclusive aqueles sem crédito:

```bash
curl \
  "http://127.0.0.1:8000/commercial-events?source=csv-example&limit=25"
```

A listagem usa paginação por cursor. Reutilize os mesmos filtros ao enviar o
`next_cursor`; não existe paginação por offset nem total global.

A timeline de um colaborador também usa paginação keyset:

```bash
curl \
  "http://127.0.0.1:8000/collaborators/employee-1/financial-timeline?entry_type=credit&currency=BRL&limit=25"
```

Ela retorna lançamentos reais e metadados mínimos dos eventos relacionados,
sem recalcular remuneração ou expor payloads.

Uma execução listada no drill-down do evento pode ser auditada por:

```bash
curl \
  "http://127.0.0.1:8000/processing-runs/processing-run-id"
```

São expostos somente estado persistido da execução, evento relacionado e
`phase`, `status` e `can_continue` de cada fase, na ordem original.

Para consultar métricas factuais do processamento persistido:

```bash
curl \
  "http://127.0.0.1:8000/processing/health?start_date=2026-07-01&end_date=2026-07-31"
```

`GET /health` continua sendo apenas liveness do processo. Já
`GET /processing/health` consulta o banco e contabiliza execuções por status e
versão, além de eventos com ou sem execução, reprocessamento e Ledger. As datas
são inclusivas sobre `ProcessingRun.started_at`; não há score, diagnóstico ou
período implícito.

Para localizar as execuções que compõem essas métricas:

```bash
curl \
  "http://127.0.0.1:8000/processing-runs?final_status=posted&limit=20"
```

A listagem ordena por `started_at` e ID decrescentes e retorna `next_cursor`
quando houver outra página. O cursor é opaco e deve ser enviado com os mesmos
filtros:

```bash
curl \
  "http://127.0.0.1:8000/processing-runs?limit=2&cursor=CURSOR"
```

O fluxo investigativo parte de `/processing/health`, filtra
`/processing-runs`, abre `/processing-runs/{id}` e, quando necessário, navega
para `/commercial-events/{event_id}`.

## Qualidade e testes

```bash
uv --project backend run ruff check backend
uv --project backend run pytest backend/tests
```

A documentação principal do projeto está no [README da raiz](../README.md) e
na pasta [`docs/`](../docs/).
