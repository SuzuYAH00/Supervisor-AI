# Frontend do Supervisor AI

Fundação React do frontend operacional interno. A primeira tela disponível é
`/processing-health`, que consome `GET /processing/health` da API MVP v1.

## Stack

- React e TypeScript strict;
- Vite;
- React Router;
- fetch nativo;
- Vitest e Testing Library;
- ESLint.

## Instalação

Requisitos: Node.js 22 e npm.

```bash
cd frontend
npm install
cp .env.example .env
```

## Configuração

O cliente lê `VITE_API_BASE_URL` em um único módulo. Para desenvolvimento, o
valor padrão `/api` usa o proxy do Vite:

```env
VITE_API_BASE_URL=/api
VITE_DEV_API_TARGET=http://127.0.0.1:8000
```

Assim, não é necessário habilitar CORS no backend local. Em uma publicação
futura, configure `VITE_API_BASE_URL` com a origem ou caminho público correto.

## Execução local

Inicie o backend, com migrations previamente aplicadas:

```bash
cd backend
SUPERVISOR_AI_DATABASE_URL="sqlite+pysqlite:///supervisor_ai.sqlite3" \
  .venv/bin/uvicorn \
  supervisor_ai.main:create_application_from_environment --factory
```

Em outro terminal:

```bash
cd frontend
npm run dev
```

Acesse `http://localhost:5173`. A raiz redireciona para
`/processing-health`.

## Qualidade

```bash
npm run lint
npm run typecheck
npm test
npm run build
```

## Organização

- `src/app`: roteamento e composição da aplicação;
- `src/components`: layout e feedback reutilizável;
- `src/features/processing-health`: API, tipos, hook, componentes e página;
- `src/lib`: configuração e cliente HTTP sem dependência de React;
- `src/styles`: estilos globais e responsivos;
- `tests`: contratos HTTP, feature e roteamento.

O cliente HTTP valida o envelope de erro da API, suporta cancelamento e não
expõe respostas técnicas. O contrato de Processing Health é validado em runtime
antes de chegar à tela.

## Limitações atuais

- sem autenticação ou autorização;
- apenas a tela de Processing Health está ativa;
- navegação financeira, eventos, execuções e timeline está marcada como
  “Em breve”;
- sem upload CSV, filtros editáveis, gráficos avançados ou estado global;
- sem deploy, telemetria ou atualização automática.
