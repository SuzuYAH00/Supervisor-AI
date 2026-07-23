# Frontend do Supervisor AI

Fundação React do frontend operacional interno. As telas disponíveis são
`/processing-health`, que consome `GET /processing/health`, e
`/financial-summary`, que consome `GET /financial/summary`, e
`/commercial-events`, que consome `GET /commercial-events`, e
`/financial-timeline`, que consome a timeline financeira por colaborador da API
MVP v1, e `/processing-runs`, que consome `GET /processing-runs`.

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
- `src/features/financial-timeline`: formulário, Ledger factual e paginação;
- `src/features/processing-runs`: listagem factual das execuções e paginação;
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
- `/financial-timeline`: lançamentos financeiros de um colaborador informado.
- `/processing-runs`: execuções persistidas do pipeline.

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

## Timeline financeira

A timeline começa sem requisição. O valor digitado permanece separado do
`collaborator_id` submetido: espaços externos são removidos somente no envio e
maiúsculas e minúsculas são preservadas.

Cada nova consulta limpa dados, erros e histórico de cursores. A paginação usa
o mesmo cursor opaco da API e mantém o retorno somente em memória. Retry repete
o colaborador e o cursor efetivamente submetidos. Requisições anteriores são
abortadas e também protegidas por ciclo ativo, impedindo respostas obsoletas de
substituírem a consulta atual.

A API atual não informa existência cadastral do colaborador: qualquer
identificador válido sem lançamentos retorna HTTP 200 e timeline vazia. O
frontend não infere existência a partir desse resultado. Enquanto não houver
um código público específico, respostas HTTP de erro, inclusive 404, seguem o
feedback genérico da aplicação.

A tabela apenas projeta Ledger, referências e evento de origem. Não calcula
saldo, total, agrupamento, comissão ou status derivado.

## Execuções de processamento

A tela consulta automaticamente a primeira página de `GET /processing-runs`.
Ela projeta identificadores, origem, referência externa, timestamps, status
final e versão do motor de regras exatamente como recebidos. Não calcula
duração, percentuais, totalizadores nem diagnóstico operacional.

`next_cursor` é tratado como opaco. O avanço envia o cursor retornado e o
retorno usa um histórico mantido apenas enquanto a tela está montada. Retry
repete a posição solicitada, a troca de página remove os dados anteriores e
requisições são protegidas por cancelamento e ciclo ativo. Não há filtros
visuais nesta versão, embora o cliente tipado represente os filtros públicos.

Os componentes de paginação continuam locais às três features. Apesar da
semelhança visual, seus contratos diferem (`has_more`, consulta por colaborador
e textos de contexto); generalizá-los agora aumentaria a superfície das telas
já aprovadas.

## Limitações atuais

- sem autenticação ou autorização;
- Processing Health, Resumo Financeiro, Eventos Comerciais, Timeline
  Financeira e Execuções de Processamento estão ativos;
- sem upload CSV, filtros editáveis, gráficos avançados ou estado global;
- sem deploy, telemetria ou atualização automática.
