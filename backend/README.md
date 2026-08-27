# Backend do Supervisor AI

Aplicação FastAPI responsável pela API e pela infraestrutura dos motores de
importação, processamento e regras do Supervisor AI.

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

## PostgreSQL externo do MK

O conector MK usa uma configuração independente do banco operacional do
Supervisor AI. Ele é opcional: sua ausência ou indisponibilidade não impede a
inicialização normal da aplicação. As variáveis aceitas estão documentadas no
`.env.example` com os nomes `MK_DB_*`; credenciais reais devem permanecer fora
do repositório.

A conexão é estritamente read-only, usa pool de duas conexões sem overflow,
reciclagem após cinco minutos, timeout de conexão de cinco segundos e timeout
de statement de quinze segundos. O health check do conector executa somente
`SELECT 1` e `SHOW transaction_read_only`. A origem utiliza timestamps sem
timezone interpretados como `America/Fortaleza`; mappers futuros serão
responsáveis pela conversão explícita para UTC.

O modo TLS padrão é `require`. Ambientes com uma CA confiável devem usar
`MK_DB_SSLMODE=verify-full` (e configurar o certificado no mecanismo seguro da
plataforma). Não é aceito modo que desabilite TLS.

### Contratos de consulta MK

O conector fornece gateways tipados e exclusivamente read-only para
`mk_atendimento`, `mk_dialogo_sessao`, `mk_dialogo_sessao_operador` e
`fr_usuario`. As listagens usam cursor pela chave primária crescente, com
`WHERE pk > :after_id`, `ORDER BY pk` e `LIMIT`; não usam `OFFSET` nem
`SELECT *`. Operadores de conversas e usuários são carregados por consultas em
lote para evitar N+1.

Datas e timestamps retornados continuam representando o valor civil bruto do
MK, sem timezone. A conversão explícita de `America/Fortaleza` para UTC pertence
à futura camada de processamento. `nota IS NULL` permanece `None`, sem conversão
para `-1`. Os contratos comerciais de Upgrade permanecem fora desta camada até
a auditoria factual do respectivo schema.

### Espelho operacional MK

O banco interno possui um espelho operacional mutável separado dos fatos
consolidados:

```text
PostgreSQL MK (read-only)
  -> contratos externos MK
  -> mk_attendance_mirror / mkbot_conversation_mirror
  -> processamento e projeções futuras
```

`external_id` preserva, como texto, `codatendimento` ou
`cod_dialogosessao`. Uma releitura com os mesmos fatos é `UNCHANGED`; mudanças
factuais posteriores, como encerramento, operador final ou avaliação, atualizam
a mesma linha. `source_first_seen_at` e `source_last_seen_at` são metadados da
sincronização, enquanto `local_created_at` e `local_updated_at` descrevem a
persistência local.

O relacionamento atendimento/conversa usa exclusivamente
`mk_atendimento.cd_dialogo -> mk_dialogo_sessao.cod_dialogosessao`. A referência
externa pode existir antes da conversa local, evitando dependência da ordem de
sincronização; protocolo não é usado como chave de relacionamento.

Os timestamps naive da origem são interpretados explicitamente em
`America/Fortaleza` e convertidos para UTC antes da persistência. `score = NULL`
continua `NULL`; esta camada não produz o sentinela `-1` das planilhas.

`mk_sync_states` mantém um único cursor de PK por fonte/entidade. O cursor e os
upserts usam a mesma Unit of Work, permitindo que uma sincronização futura faça
commit por lote. `mk_sync_runs` registra contagens e resultado de cada execução
sem reutilizar `processing_runs`, cuja semântica é vinculada ao processamento de
eventos comerciais.

Campos factuais tratados como mutáveis incluem encerramento, status, operadores,
processo, subprocesso, classificações, vínculo com diálogo, timestamps da
conversa e avaliação. A identidade externa nunca é alterada. A resolução dos IDs
de operador para colaboradores e as projeções em `AttendanceFact`/`CsatContact`
pertencem às próximas etapas.

### Identidade de operadores MK

A identidade canônica de um operador MK é
`source="mk" + external_identity=str(fr_usuario.usr_codigo)`. Ela reutiliza
`CollaboratorExternalIdentity`: o vínculo é cadastrado explicitamente para um
colaborador existente e a chave `(source, external_identity)` impede que o
mesmo `usr_codigo` pertença a dois colaboradores.

`usr_login`, `usr_nome` e textos presentes nos relatórios não são identidades e
não produzem associação automática. A resolução em lote faz uma única consulta,
remove IDs repetidos e devolve separadamente correspondências exatas e IDs que
exigem mapping manual. Operadores desconhecidos continuam preservados nos
mirrors; sua ausência no cadastro não bloqueia a captura do fato MK.

O contrato PostgreSQL atual expõe IDs de usuários ligados às sessões, mas não
identifica factualmente qual `usr_codigo` representa `MKBOT assistant`. Até essa
identidade ser comprovada, a regra textual já existente no importador XLSX é
apenas um fallback legado e não é aplicada ao espelho PostgreSQL.

### Sincronização de atendimentos MK

`SyncMkAttendancesUseCase` lê `mk_atendimento` em páginas de até 1.000 registros
(padrão 500), sempre por `codatendimento > cursor`, e grava somente
`mk_attendance_mirror`. Cada lote executa os upserts e atualiza o cursor na mesma
Unit of Work; qualquer falha reverte todo o lote e mantém o cursor anterior.

O cursor crescente cobre registros novos, mas não alterações tardias. Por isso,
cada execução também pode reconciliar em lote os atendimentos locais ainda
abertos e uma janela recente configurável. A janela padrão é de sete dias e
`reconcile_from` permite informar uma data explícita, inclusive para futuras
políticas de cobertura de coorte, sem acoplar o sync à regra de Reincidência.
Consultas de abertos usam lotes de IDs com limite de 1.000; ausência na resposta
externa nunca provoca exclusão local.

O estado `(source="mk", entity_type="attendance")` funciona como cursor e lock.
O início marca o estado como `RUNNING`; cada transação usa bloqueio da linha e
confere o cursor esperado. Uma segunda execução é rejeitada enquanto o estado
estiver em andamento. Sucesso e falha são registrados em `mk_sync_runs`, com
contadores e erros sanitizados.

Datas naive do MK são interpretadas em `America/Fortaleza` pela função central e
persistidas em UTC. Operadores desconhecidos e `cd_dialogo` são preservados como
IDs externos; nenhum mapping de colaborador é obrigatório para capturar o fato.
Esta etapa não cria `AttendanceFact`, não executa regras, não agenda jobs e não
substitui os importadores atuais.

### Projeção de atendimentos MK

`ProjectMkAttendancesUseCase` mantém separadas a captura e a consolidação:

```text
PostgreSQL MK -> sync -> mk_attendance_mirror
                             |
                             v
                    projeção controlada
                             |
                             v
                       AttendanceFact -> regra existente de Reincidência
```

A projeção usa `source="mk_postgresql"` e
`external_reference=str(codatendimento)`, distinguindo o caminho PostgreSQL do
legado `source="mk"`. O protocolo textual continua no mirror e no resultado da
projeção; ele não é identidade nem relógio. `opened_at` preserva a precisão e é
a autoridade cronológica, inclusive para vários atendimentos do mesmo cliente
no mesmo dia.

Somente atendimentos factualmente finalizados, com encerramento, cliente,
operador de encerramento, origem, processo e classificações são candidatos. A
documentação normativa de Reincidência registra que a planilha operacional usa
o operador que encerrou o atendimento como responsável. O operador é resolvido
exclusivamente por `usr_codigo` via
`CollaboratorExternalIdentity`; ausência de vínculo produz
`UNRESOLVED_OPERATOR`. Como o mirror contém IDs dos catálogos, códigos e
descrições usados pela regra devem vir de um catálogo explícito; valores não
resolvidos produzem `UNRESOLVED_CATALOG`, sem texto inventado.

A auditoria read-only do PostgreSQL comprova os joins e rótulos
`mk_ate_processos.codprocesso/nome_processo`,
`mk_ate_subprocessos.codsubprocesso/nome_subprocesso`,
`mk_atendimento_classificacao.codatclass/descricao` e
`mk_origem_contato.cd_orig_cont/origem_contato`. Esses IDs internos não são os
códigos operacionais exibidos no relatório: por exemplo, fixtures factuais usam
PK de processo `44`, enquanto a regra consome o código `01`. As tabelas não
possuem uma coluna separada para o código operacional: o banco persiste o rótulo
canônico completo, como `01 - Atendimento Suporte`. O repositório lê os quatro
catálogos uma vez por execução, sem N+1, e o processamento relaciona o rótulo
completo às identidades normativas conhecidas, sem separar ou inferir seu
prefixo. Divergências históricas de apresentação são aliases explícitos e
testados; valores desconhecidos permanecem não elegíveis.

O mapa semântico adotado é: cliente e protocolo são `EXACT`; abertura é
`BETTER_PRECISION`; responsável usa factualmente o operador de encerramento;
processo, classificações e origem são `DERIVABLE` por resolução factual dos
catálogos. A identidade e a
idempotência usam `codatendimento`, nunca protocolo.

`compare_recurrence_paths` executa a mesma regra sobre conjuntos separados e
classifica diferenças de precisão, data sem horário, protocolo legado
corrompido, operador, ausência de registro e diferença semântica. Ele não muda a
fonte oficial: importadores XLSX/CSV e consultas vigentes permanecem ativos até
o dual-run ser aprovado.

## API MVP v1

| Método | Rota | Finalidade |
| --- | --- | --- |
| GET | `/health` | Liveness do processo, sem acessar o banco |
| POST | `/imports/csv` | Importar um CSV com atomicidade por documento |
| GET | `/financial/snapshot` | Consultar créditos financeiros detalhados |
| GET | `/financial/summary` | Agregar créditos por colaborador e moeda |
| GET | `/commercial-events` | Localizar eventos comerciais |
| GET | `/commercial-events/{id}` | Auditar evento, Ledger e execuções |
| GET | `/collaborators/{id}/financial-timeline` | Navegar lançamentos do colaborador |
| GET | `/processing-runs` | Localizar execuções persistidas |
| GET | `/processing-runs/{id}` | Auditar as fases públicas de uma execução |
| GET | `/processing/health` | Consultar métricas factuais de processamento |

Fluxo principal para um frontend:

1. importar o CSV;
2. consultar snapshot ou resumo financeiro;
3. localizar eventos comerciais;
4. consultar a saúde factual do processamento;
5. filtrar execuções;
6. abrir a execução;
7. abrir o evento relacionado;
8. consultar a timeline do colaborador.

Datas de consulta são ISO 8601; as janelas documentadas são inclusivas em UTC.
Datas e horários retornados possuem offset explícito. Dinheiro é representado
como string decimal.

As listagens usam cursor opaco e não fornecem `total_count`. Os mesmos filtros
devem acompanhar o `next_cursor` na página seguinte. Respostas de erro usam:

```json
{
  "error": {
    "code": "invalid_query_parameters",
    "message": "Request parameters are invalid"
  }
}
```

Esta API ainda não possui autenticação ou autorização. A única entrada de
arquivo do MVP é CSV; não há integração direta com MK, frontend, reprocessamento
HTTP, filas ou automações. O marco MVP v1 define um contrato interno estável
para integração com o frontend, não prontidão para exposição pública em
produção.

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
