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
uv --project backend run uvicorn supervisor_ai.main:app --reload
```

A API ficará disponível em `http://localhost:8000`. O endpoint de saúde está
disponível em `http://localhost:8000/health`.

## Qualidade e testes

```bash
uv --project backend run ruff check backend
uv --project backend run pytest backend/tests
```

A documentação principal do projeto está no [README da raiz](../README.md) e
na pasta [`docs/`](../docs/).
