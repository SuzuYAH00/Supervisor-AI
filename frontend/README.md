# Frontend do Supervisor AI

Fundação React do frontend operacional interno. As telas disponíveis são
`/processing-health`, que consome `GET /processing/health`, e
`/financial-summary`, que consome `GET /financial/summary`, e
`/commercial-events`, que consome `GET /commercial-events` da API MVP v1.

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
- `src/features/financial-summary`: resumo financeiro com a mesma separação;
- `src/features/commercial-events`: listagem factual e paginação por cursor;
- `src/lib`: configuração e cliente HTTP sem dependência de React;
- `src/styles`: estilos globais e responsivos;
- `tests`: contratos HTTP, feature e roteamento.

O cliente HTTP valida o envelope de erro da API, suporta cancelamento e não
expõe respostas técnicas. O contrato de Processing Health é validado em runtime
antes de chegar à tela. A mesma validação explícita protege o resumo financeiro;
valores monetários permanecem strings decimais e não são convertidos em
`number`.

## Rotas

- `/processing-health`: métricas factuais da saúde do processamento;
- `/financial-summary`: créditos consolidados por moeda e colaborador.
- `/commercial-events`: eventos persistidos, em ordem e páginas da API.

A tela financeira projeta somente os totais e agrupamentos entregues pela API.
Ela não calcula ranking, percentual, produtividade, tendência ou conversão
entre moedas; posições e participações já retornadas pela API são apenas
exibidas.

## Paginação dos eventos

A listagem comercial trata `next_cursor` como valor opaco. “Próxima página”
envia o cursor recebido, enquanto “Página anterior” reutiliza o histórico
mantido somente durante a sessão da tela. O cursor não é decodificado nem
persistido. A indicação “Página N desta sessão” representa apenas a navegação
local, não uma posição absoluta no banco.

A tela não oferece filtros editáveis nesta etapa, embora seu cliente tipado
suporte todos os filtros públicos da API. Também não calcula estado, crédito,
estatística ou interpretação comercial.

## Limitações atuais

- sem autenticação ou autorização;
- Processing Health, Resumo Financeiro e Eventos Comerciais estão ativos;
- navegação de execuções e timeline está marcada como
  “Em breve”;
- sem upload CSV, filtros editáveis, gráficos avançados ou estado global;
- sem deploy, telemetria ou atualização automática.
