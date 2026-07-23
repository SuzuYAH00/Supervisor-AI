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

## Qualidade e testes

```bash
uv --project backend run ruff check backend
uv --project backend run pytest backend/tests
```

A documentação principal do projeto está no [README da raiz](../README.md) e
na pasta [`docs/`](../docs/).
