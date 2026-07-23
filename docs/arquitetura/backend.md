# Arquitetura Backend do Supervisor AI

## 1. Objetivo

O backend do Supervisor AI será responsável por controlar toda a lógica de funcionamento da plataforma.

Ele será a camada responsável por:

- Coletar informações dos sistemas externos;
- Processar dados;
- Aplicar regras de negócio;
- Armazenar informações;
- Gerar análises;
- Disponibilizar informações para a interface do usuário.

O backend será o núcleo operacional do Supervisor AI.

---

# 2. Responsabilidades principais

## Coleta de dados

Responsável por buscar informações dos sistemas externos.

Exemplos:

- Atendimentos do NPX;
- Atendimentos do MKBot;
- Tickets do MK Workspace;
- Pagamentos do MK Financeiro;
- Dados de ponto;
- Dados de extras.

---

## Processamento de dados

Responsável por transformar dados brutos em informações úteis.

Exemplo:

Entrada:

```
Atendimento encerrado
Nota do cliente: 10
Operador: João
```

Processamento:

```
Identificar operador

Atualizar CSAT

Calcular média

Comparar com equipe

Gerar indicador
```

---

## Regras de negócio

Responsável por aplicar as regras definidas pela empresa.

Exemplos:

- Cálculo de Upgrade;
- Cálculo de RV;
- Cálculo de Extras;
- Identificação de reincidência;
- Critérios de cancelamento.

---

## Geração de inteligência

Responsável por utilizar os dados processados para gerar informações úteis.

Exemplos:

- Alertas;
- Resumos diários;
- Identificação de padrões;
- Sugestões de ação.

---

# 3. Fluxo geral do backend

O funcionamento esperado:

```
Sistemas externos

↓

Coletores

↓

Banco de dados

↓

Processadores

↓

Regras de negócio

↓

Camada de inteligência

↓

Interface Supervisor AI
```

---

# 4. Módulos internos do backend

## Módulo de integração

Responsável pela comunicação com sistemas externos.

Exemplos:

- MK Solutions;
- NPX;
- MKBot;
- Colabore;
- AppSheet.

Responsabilidades:

- Autenticação;
- Consulta;
- Recebimento de dados;
- Tratamento inicial.

---

# Módulo de sincronização

Responsável por controlar quando os dados serão atualizados.

Exemplos:

Atualização de indicadores:

```
14:00

17:00

22:00
```

Responsabilidades:

- Executar rotinas automáticas;
- Controlar histórico;
- Evitar duplicação.

---

# Módulo de processamento

Responsável por transformar dados coletados.

Exemplos:

Atendimentos:

```
Dados do MKBot

↓

Separação por operador

↓

Cálculo CSAT

↓

Indicador atualizado
```

---

# Módulo de regras de negócio

Centraliza as regras operacionais.

Exemplos:

## Upgrade

Avaliar:

- Mudança de plano;
- Valor novo;
- Pagamento;
- Elegibilidade.

---

## RV

Avaliar:

- CSAT;
- Reincidência;
- Qualidade;
- Atrasos;
- Faltas.

---

## Extras

Avaliar:

- Horários;
- Intervalo;
- Tipo de extra;
- Conflitos de jornada.

---

# Módulo financeiro

Responsável pela consolidação dos valores pagos.

Exemplos:

```
Upgrade

+

RV

+

Extras

=

Pagamento total
```

---

# Módulo de alertas

Responsável por identificar situações importantes.

Exemplos:

- Operador abaixo da média;
- Crescimento de cancelamentos;
- Queda de indicador;
- Necessidade de ação.

---

# 5. Processamento automático

O Supervisor AI deve reduzir atividades manuais através de rotinas automáticas.

Exemplo atual:

```
Supervisor exporta MK

↓

Atualiza planilha

↓

Calcula indicadores

↓

Atualiza dashboard
```

Fluxo futuro:

```
Supervisor AI consulta MK

↓

Processa dados

↓

Atualiza indicadores

↓

Exibe informações
```

---

# 6. Controle de duplicidade

Como alguns sistemas trabalham com exportações periódicas, o backend deverá controlar registros duplicados.

Exemplo atual:

Exportação 14h:

```
Todos atendimentos até 14h
```

Exportação 17h:

```
Todos atendimentos até 17h

-

Atendimentos já coletados
```

O Supervisor AI deverá utilizar identificadores únicos para evitar registros repetidos.

Exemplos:

- Protocolo;
- ID atendimento;
- Código cliente.

---

# 7. Histórico de processamento

Todas as execuções importantes devem ser registradas.

Exemplos:

- Última sincronização;
- Quantidade de dados importados;
- Erros encontrados;
- Alterações realizadas.

---

# 8. Integração com Inteligência Artificial

A IA será uma camada adicional utilizando os dados processados pelo backend.

Ela não deve acessar dados brutos diretamente.

Fluxo:

```
Sistemas

↓

Backend

↓

Dados organizados

↓

IA

↓

Resposta ao gestor
```

---

# 9. Segurança

O backend deverá controlar:

- Permissões;
- Acesso por perfil;
- Dados sensíveis;
- Histórico de alterações.

Exemplo:

Supervisor:

- Visualiza sua operação.

Gerente:

- Visualiza todas equipes.

Administrador:

- Gerencia configurações.

---

# 10. Evolução futura

Possíveis evoluções:

- Integrações em tempo real;
- Automações de processos;
- Previsões utilizando IA;
- Recomendações automáticas;
- Assistente operacional completo.

---

# 11. Stack técnica

O backend será implementado como um monólito modular utilizando:

- Python 3.12;
- FastAPI;
- PostgreSQL;
- SQLAlchemy 2.x;
- psycopg 3;
- Alembic;
- pytest;
- Ruff;
- uv.

As operações de banco de dados serão síncronas inicialmente.

No ambiente local, o Docker Compose será utilizado somente para executar o PostgreSQL. A aplicação Python será executada diretamente no ambiente gerenciado pelo uv.

A decisão e seus critérios de revisão estão registrados em `docs/adr/ADR-003.md`.

---

# 12. Fluxo transacional de eventos comerciais

O caso de uso `ProcessAndPersistCommercialEventUseCase`, na camada Application,
coordena a primeira materialização transacional do fluxo de remuneração. Ele
recebe um evento comercial e um contexto de avaliação, delega todas as decisões
ao `ProcessCommercialEventUseCase` e persiste os fatos resultantes.

Uma única Unit of Work abrange:

1. localização ou inclusão do evento comercial;
2. execução do fluxo puro do Rules Engine;
3. registro de uma nova execução de processamento;
4. inclusão idempotente do lançamento produzido;
5. commit explícito após todas as gravações.

O caso de uso não interpreta o conteúdo das decisões das fases e não conhece
SQLAlchemy, banco de dados ou modelos ORM. Clock, gerador do identificador da
execução e fábrica de Unit of Work são dependências injetadas. Uma exceção antes
do commit encerra a Unit of Work com rollback, inclusive quando o evento tiver
sido incluído na mesma tentativa.

## Reprocessamento e idempotência

A referência externa identifica de forma única um evento persistido. Um comando
repetido é aceito quando mantém identificador interno, origem, instante de
ocorrência e payload. Os instantes de recebimento e criação são metadados
técnicos e não mudam a identidade comercial. Cada reprocessamento aceito gera um
novo `ProcessingRun`, preservando o histórico das avaliações.

Antes de inserir um crédito, a Application procura o crédito do evento. Um
lançamento integralmente igual é tratado como já existente e não é duplicado.
Um lançamento divergente gera `LedgerConflict`. A reutilização da referência
externa com identidade ou payload divergente gera `CommercialEventConflict`.
Constraints únicas no banco permanecem como proteção contra concorrência; erros
técnicos de integridade não são convertidos silenciosamente em sucesso.

## Auditoria das fases

Cada execução armazena, por fase, somente o contrato estável conhecido pela
Application: nome, status, continuidade, avisos e referências de auditoria. O
campo `output` não é persistido nesta etapa, pois cada fase possui um contrato
próprio e ainda não existe uma representação JSON pública comum. Essa omissão
evita `repr`, pickle ou serialização implícita de objetos internos do motor.

---

# 13. Composition Root

O módulo `supervisor_ai.bootstrap` é o Composition Root inicial do backend. Ele
constrói explicitamente o grafo de objetos necessário para processar e persistir
eventos comerciais:

- engine e SessionFactory do SQLAlchemy;
- fábrica de Unit of Work;
- handlers das sete fases do fluxo comercial;
- avaliadores puros do Rules Engine;
- `ProcessCommercialEventUseCase`;
- clock do sistema e gerador UUID para execuções;
- `ProcessAndPersistCommercialEventUseCase`.

As funções públicas `build_session_factory`, `build_unit_of_work_factory`,
`build_rules_engine` e `build_transactional_processor` permitem montar o grafo
completo ou suas partes principais sem Service Locator e sem singletons globais.
Cada chamada produz dependências explícitas e independentes.

## Limite arquitetural

O bootstrap é a única camada autorizada a conhecer simultaneamente Application,
Rules Engine e Infrastructure. Essa autorização existe somente para conectar
objetos. O módulo não contém regras comerciais, não executa consultas por conta
própria e não expõe modelos ORM à Application.

As dependências continuam apontando para dentro:

```text
Composition Root
    ├── Application
    ├── Rules Engine
    └── Infrastructure

Application ──→ contratos públicos do Rules Engine
Infrastructure ──→ portas da Application
Rules Engine ──→ nenhuma infraestrutura
```

## Entrada financeira opcional

O contexto contratual pode ser processado sem snapshot financeiro. Nessa forma
compatível, os handlers executam as fases financeiras com ausência explícita de
evidência; os avaliadores respondem `not_evaluable` e nenhum lançamento é
inventado. Quando `FinancialSnapshot` é fornecido, o mesmo pipeline pode validar
pagamento, calcular remuneração e produzir um lançamento real.

---

# 14. Entrada JSON do Import Engine

A primeira porta de entrada do Import Engine recebe um único documento JSON e o
transforma no comando público `ProcessAndPersistCommercialEventCommand`. O
adapter está em `infrastructure.importing`, pois JSON é uma preocupação de
transporte e não pertence à Application nem ao Rules Engine.

O fluxo é explícito:

```text
Texto JSON
    ↓
Parser estrito
    ↓
Validação do schema
    ↓
Mapeamento para CommercialEvent, EvaluationContext e Evidence
    ↓
ProcessAndPersistCommercialEventUseCase
```

## Schema inicial

O objeto raiz aceita exatamente:

- `event`: `id`, `external_reference`, `source`, `occurred_at`, `received_at` e
  `raw_payload`;
- `evaluation`: `evaluation_id`, `subject_id`, `observed_at` e `evidence`;
- `rules_engine_version`.

Cada item de `evaluation.evidence` aceita exatamente `id`, `name`, `value` e
`observed_at`. Os nomes são validados diretamente pelos enums públicos
`ContractualEvidenceName` e `OperationalFactName`. Decisões derivadas não são
aceitas como evidência de transporte.
Os envelopes são fechados; somente `raw_payload` é um objeto JSON aberto,
preservado sem descarte de campos.

## Parsing e validação

O parser usa `json.loads`, rejeita chaves duplicadas e números não finitos como
`NaN` e `Infinity`. A validação rejeita campos ausentes ou desconhecidos, tipos
incompatíveis, strings obrigatórias vazias, UUIDs inválidos, datas sem timezone,
nomes de evidência desconhecidos e IDs de evidência repetidos. As mensagens
incluem o caminho do campo que falhou.

Datas ISO 8601 aceitam `Z` ou offset explícito e são normalizadas para UTC no
mapeamento. Não há coerção de strings: `"500"` não se torna inteiro e `"true"`
não se torna booleano. Arrays de adicionais tornam-se tuplas porque esse é o
contrato imutável do Rules Engine. Valores numéricos das evidências recorrentes
são convertidos explicitamente para `Decimal`; essa conversão é determinada
pelo nome da evidência e não se aplica ao `raw_payload`.

## Erros e composição

Erros próprios do documento usam `ImportDocumentError`, `JsonSyntaxError` e
`ImportValidationError`. Conflitos da Application, erros de integridade e falhas
inesperadas do processador não são capturados nem convertidos pelo importer.

`build_json_importer(database_url)` reutiliza
`build_transactional_processor(database_url)` e não duplica a montagem do
pipeline. A execução pode terminar em `not_evaluable` quando
`financial_snapshot` não for enviado. O campo opcional permite completar as
fases financeiras sem quebrar os documentos anteriores.

---

# 15. Snapshot financeiro público

`FinancialSnapshot` é o contrato imutável da Application que transporta somente
fatos financeiros já observados para validação de pagamento, cálculo da
remuneração e postagem no ledger. Ele não contém classificações comerciais nem
decide se há direito ao crédito.

O contrato é dividido em:

- `PaymentFacts`: avaliação, fatura, vencimento, pagamento, valores, vínculos,
  candidatos, referências e flags de consistência;
- `RemunerationFacts`: valores-base, adicional, fidelidade, referências e flags
  de consistência;
- `RemunerationPostingFacts`: beneficiário, instante, referências de postagem,
  cálculo e fontes.

Os handlers somente convertem essas dataclasses e as conclusões anteriores nos
inputs públicos existentes. O tipo comercial consumido pelo cálculo é traduzido
das decisões da fase de classificação, nunca do snapshot ou do JSON. Ausências
e conflitos continuam sendo interpretados pelos evaluators. Nenhum handler
consulta banco, completa informação faltante ou reexecuta regra comercial.

## Snapshot ausente ou parcial

`ProcessCommercialEventCommand` aceita `financial_snapshot=None`. Nesse caso,
as fases financeiras retornam `not_evaluable` e não criam ledger.

Quando o snapshot existe, campos de negócio opcionais podem ser nulos. Um
snapshot parcial mantém esses valores como `None`; não usa relógio, UUID, zero,
`False` ou string vazia como substitutos. O evaluator determina o status seguro.

## Dinheiro no JSON

Campos monetários de `financial_snapshot` usam strings decimais canônicas, como
`"119.90"`. Números JSON, expoentes, negativos, `NaN`, `Infinity`, prefixo
positivo e zeros à esquerda são rejeitados. O mapper converte a string
diretamente para `Decimal`, sem passagem por `float`.

Essa política não altera `raw_payload`, que permanece uma árvore JSON aberta.

## Determinismo e identidade econômica

O identificador do crédito é estável por evento:

```text
entry_id = "ledger.remuneration.credit:" + event_id
```

O handler não usa `uuid4` nem `datetime.now`. `posted_at`, referências,
beneficiário e fatura vêm do snapshot. O mesmo evento com os mesmos fatos produz
o mesmo `LedgerEntry`.

No reprocessamento, um lançamento integralmente igual não é inserido novamente.
Um lançamento divergente gera `LedgerConflict`; a constraint única por crédito e
evento permanece como proteção concorrente.

## Preparação das evidências operacionais

O adapter reconhece somente `OperationalFactName` no conjunto operacional do
array de evidências e os prepara como fatos rastreáveis antes das regras. As
regras operacionais produzem `OperationalDecisionName`; não há conversão por
semelhança textual. As decisões comerciais vêm exclusivamente da fase de
classificação. Assim, o Import Engine transporta observações e nunca injeta
conclusões de domínio.

---

# 16. Processamento em lote

O `BatchImportProcessor` coordena uma coleção ordenada de documentos já
preparados para um importer. Seu núcleo é genérico: `BatchDocument[T]` associa
um identificador auditável a um payload opaco e `DocumentImporter[T]` representa
a única operação necessária. Por isso, o componente não conhece JSON, CSV,
SQLAlchemy, API, arquivos ou sistemas externos.

O Composition Root especializa inicialmente esse contrato com texto JSON por
meio de `build_batch_processor(database_url)`. O builder reutiliza integralmente
`build_json_importer()`; parsing, validação, mapeamento, regras e persistência não
são duplicados no lote. Conectores futuros de CSV, API ou upload poderão produzir
outro `T` e fornecer um importer compatível sem alterar os contratos do batch.

## Atomicidade e falhas parciais

Cada item chama o importer de forma independente. O importer transacional abre,
confirma, reverte e fecha sua própria Unit of Work antes de o próximo documento
começar. Não existe transação compartilhada nem rollback global do lote.

Falhas são registradas no resultado individual e não interrompem os itens
seguintes:

- erros do documento, inclusive sintaxe e validação, são
  `validation_error`;
- `CommercialEventConflict` e `LedgerConflict` são `business_conflict`;
- exceções inesperadas são `technical_error`, preservando tipo e mensagem.

`BatchDocumentResult` registra identificadores, status final, criação ou
reutilização de evento e ledger, avisos, referências de auditoria e duração.
`BatchStatistics` consolida documentos, categorias de falha, execuções e novos
lançamentos. `BatchImportResult` preserva a ordem, início, fim e duração total.
Todos esses contratos são imutáveis.

O processamento do MVP é deliberadamente sequencial e síncrono. A coordenação
por item mantém um ponto natural para hooks futuros, mas callbacks, threads,
`asyncio`, filas e logging externo não fazem parte desta etapa.

## Idempotência do lote

O batch não cria uma segunda política de idempotência. Reexecutar a coleção
delega cada item ao fluxo transacional existente: eventos iguais são
reutilizados, cada sucesso cria um novo `ProcessingRun` e créditos idênticos não
são duplicados. As estatísticas distinguem novos lançamentos por meio de
`ledger_persisted`.

---

# 17. Adapter de importação CSV

O `CsvImportAdapter` recebe conteúdo CSV textual e termina sua responsabilidade
ao produzir `BatchDocument[str]`. Cada documento contém JSON serializado por
`json.dumps` e segue para o mesmo `BatchImportProcessor`,
`JsonCommercialEventImporter` e fluxo transacional das demais entradas. O
adapter não lê caminhos, não abre transações, não acessa repositórios e não
executa regras.

`build_csv_import_service(database_url)` compõe o adapter com
`build_batch_processor(database_url)`. O resultado mantém separadamente
`CsvParseResult`, para estrutura e linhas do CSV, e `BatchImportResult`, para
validação do importer, conflitos e falhas técnicas.

## Schema fechado

Todas as colunas são obrigatórias no cabeçalho, embora valores anuláveis possam
ficar vazios. A ordem do cabeçalho é livre. Colunas ausentes, duplicadas,
desconhecidas ou que tentem fornecer classificações, decisões, elegibilidade,
valor calculado ou ledger tornam o arquivo estruturalmente inválido.

As colunas estão agrupadas assim:

- evento e avaliação: `document_identifier`, `event_id`,
  `external_reference`, `source`, timestamps, `raw_payload`, IDs da avaliação e
  `rules_engine_version`;
- fatos contratuais: velocidades, modalidades, mesh, adicionais e valores
  recorrentes anteriores e atuais;
- fatos operacionais: ticket, suporte, autoria e indicadores observados de
  duplicidade, finalidade, natureza administrativa/corretiva e conflito de
  autoria;
- snapshot financeiro: `financial_snapshot_present` e os fatos de pagamento,
  bases de remuneração e postagem já definidos pelo contrato público.

Os nomes completos e sua ordem canônica estão em `CSV_COLUMNS`. A opção por
colunas fixas mantém explícito o pequeno conjunto de fatos do fluxo atual e
evita criar uma linguagem de evidências dentro de uma célula.

## Representações

- decimais usam ponto e string canônica, como `99.90`; não passam por `float`;
- booleanos aceitam somente `true` e `false` em minúsculas;
- timestamps usam ISO 8601 com `Z` ou offset explícito;
- `raw_payload` contém um objeto JSON;
- adicionais e coleções de referências contêm arrays JSON de strings;
- vazio vira `None` somente nos campos explicitamente opcionais;
- `financial_snapshot_present=false` exige todas as demais colunas financeiras
  vazias.

As evidências monetárias contratuais do documento JSON também aceitam string
decimal canônica. Números JSON antigos continuam compatíveis, enquanto o CSV
preserva precisão sem conversão intermediária para ponto flutuante.

## Erros e rastreabilidade

Ausência ou defeito global do cabeçalho gera `CsvStructureError` e impede o
arquivo inteiro. Erros localizados geram `CsvRowError` com linha física, coluna,
valor seguro, categoria e mensagem; outras linhas continuam. Linhas totalmente
vazias são ignoradas sem renumerar as seguintes.

O `document_identifier` obrigatório torna estável a correlação entre a linha,
o `BatchDocument` e o `BatchDocumentResult`. Uma linha que não produziu
documento permanece apenas no resultado de parsing e nunca aparece como se
tivesse sido processada pelo batch.

Um exemplo completo e sem dados sensíveis está em
`docs/exemplos/importacao_comercial.csv`.

O MVP permanece síncrono, sequencial, baseado na biblioteca padrão `csv` e sem
pandas, threads, `asyncio`, leitura de arquivos ou streaming incremental. Novos
formatos podem produzir o mesmo `BatchDocument[T]` sem reutilizar detalhes do
CSV.

---

# 18. CLI de importação CSV

A CLI é a fronteira responsável por argumentos, configuração, leitura física e
apresentação do relatório. O comando público é:

```bash
supervisor-ai import-csv arquivo.csv \
  --database-url sqlite+pysqlite:///supervisor_ai.sqlite3
```

O entry point `supervisor-ai` chama `supervisor_ai.cli:main`. Também é possível
usar `python -m supervisor_ai.cli`. A CLI usa somente
`build_csv_import_service(database_url)`; não monta engine, sessão, Unit of Work,
repositórios, regras ou documentos do batch.

## Configuração e arquivo

A URL do banco segue precedência explícita:

1. `--database-url` não vazio;
2. `SUPERVISOR_AI_DATABASE_URL` não vazia;
3. erro de configuração.

Não existe banco padrão. A CLI também não aplica migrations nem chama
`create_all`. O arquivo informado deve existir, ser regular e legível. A leitura
usa `utf-8-sig`, aceitando UTF-8 com ou sem BOM, sem alterar, mover ou remover o
arquivo.

## Relatórios e correlação

`--output-format text` é o padrão e produz um resumo sem cores. `--verbose`
adiciona uma linha por resultado. `--output-format json` produz uma projeção
explícita e estável com arquivo, status geral, parsing, processamento, duração e
resultados correlacionados; mensagens fatais continuam em `stderr` e deixam
`stdout` vazio.

A correlação usa `document_identifier`, nunca posição. Para impedir ambiguidade,
o CSV Adapter transforma todas as ocorrências de um identificador duplicado em
`CSV_ROW_ERROR`; nenhuma delas chega ao batch. Conteúdo de `raw_payload`, URL e
credenciais do banco não aparecem nos relatórios.

## Exit codes

- `0`: execução integralmente bem-sucedida;
- `1`: falha parcial de linha ou documento;
- `2`: uso ou argumento inválido (`argparse`);
- `3`: arquivo ou encoding inválido;
- `4`: estrutura global do CSV inválida;
- `5`: configuração ou inicialização inválida;
- `6`: exceção fatal inesperada.

Erros esperados não exibem traceback. `--debug` libera traceback somente para
falhas fatais de inicialização ou execução; erros normais de linha permanecem no
relatório. O processamento continua sequencial e cada documento preserva sua
transação independente e a idempotência do pipeline existente.

---

# 19. API HTTP

A primeira camada HTTP usa FastAPI e `python-multipart` apenas para adaptar
requisições ao `CsvImportService`. Ela não acessa persistência, não abre Unit of
Work, não reconstrói documentos e não executa regras. O Composition Root expõe
`build_http_application(database_url)`, que injeta o resultado de
`build_csv_import_service(database_url)` na aplicação.

Para o servidor, `create_application_from_environment()` lê exclusivamente
`SUPERVISOR_AI_DATABASE_URL` e delega ao builder. Não existe aplicação global
que falhe durante import nem banco padrão. A inicialização não conecta para
health, não executa importação, não aplica migrations e não chama `create_all`.

```bash
SUPERVISOR_AI_DATABASE_URL=sqlite+pysqlite:///supervisor_ai.sqlite3 \
  uvicorn supervisor_ai.main:create_application_from_environment --factory
```

## Endpoints

`GET /health` retorna `{"status":"healthy"}` sem acessar serviço ou banco.

`POST /imports/csv` recebe multipart no campo `file`, mantém o conteúdo em
memória, aceita UTF-8 com ou sem BOM e chama diretamente
`CsvImportService.import_csv()`. O upload não é persistido em arquivo temporário.

```bash
curl -X POST \
  -F "file=@docs/exemplos/importacao_comercial.csv;type=text/csv" \
  http://127.0.0.1:8000/imports/csv
```

Resposta resumida:

```json
{
  "file": "importacao_comercial.csv",
  "status": "success",
  "parsing": {"total_data_rows": 1, "converted_rows": 1, "error_rows": 0},
  "processing": {"successful_documents": 1, "ledger_entries_created": 1},
  "duration_seconds": 0.01,
  "results": [{"line_number": 2, "status": "success"}]
}
```

O schema real inclui todas as contagens, timestamps e identificadores públicos
auditáveis.

## Política HTTP e segurança

- `200`: lote concluído, inclusive com falhas parciais;
- `400`: estrutura global do CSV inválida;
- `422`: multipart ausente, nome ausente, arquivo vazio ou encoding inválido;
- `500`: falha fatal inesperada.

Conflitos individuais permanecem no relatório como `business_conflict`; não se
transformam em `409`. Erros globais usam `{error: {code, message}}` e não expõem
exceções, traceback, `raw_payload`, URL, credenciais, SQL ou caminhos locais.

A projeção `project_csv_import_report()` pertence ao Import Engine e é usada
tanto pela CLI quanto pela API. Ela serializa explicitamente enums, datetimes,
durações e resultados em ordem física, substituindo mensagens técnicas por texto
seguro. A API preserva a mesma atomicidade e idempotência do batch: uma segunda
requisição idêntica cria novos `ProcessingRun` e zero créditos duplicados.

O escopo atual não inclui autenticação, CORS customizado, upload persistente,
background tasks, filas, consultas, versionamento ou processamento paralelo.

---

# 20. Consulta do snapshot financeiro consolidado

O `FinancialSnapshot` original permanece o contrato de fatos financeiros de
entrada de um evento. Ele alimenta validação de pagamento, cálculo e postagem,
mas não é persistido como documento recuperável. A consulta HTTP não tenta
reconstruir esses fatos nem cria um snapshot paralelo.

`GetFinancialSnapshotUseCase` é uma visão somente leitura dos créditos que o
pipeline já materializou no Ledger. Ele recebe `GetFinancialSnapshotQuery`, usa
a mesma `UnitOfWorkFactory`, solicita créditos ao `LedgerRepository` e retorna
DTOs imutáveis. Não executa regra, não recalcula remuneração e nunca chama
`commit`.

Como o ledger aceita mais de uma moeda, somar moedas diferentes produziria um
valor semanticamente inválido. Por isso, o resultado expõe
`totals_by_currency`, além de `credit_count` e itens. A agregação é apenas uma
projeção aritmética dos lançamentos existentes.

## Endpoint e filtros

```text
GET /financial/snapshot
GET /financial/snapshot?collaborator_id=collaborator-1
GET /financial/snapshot?start_date=2026-07-01&end_date=2026-07-31
```

`collaborator_id`, `start_date` e `end_date` são opcionais. Ausência de filtros
consulta todos os créditos disponíveis, sem mês, colaborador ou janela padrão.
Datas usam `YYYY-MM-DD` e filtram de forma inclusiva a data UTC de `posted_at`,
coerente com a normalização UTC da persistência. Intervalo invertido ou data
inválida retorna `422`.

Os filtros são aplicados pelo repositório SQLAlchemy. A consulta considera
somente `entry_type=credit` e ordena por `posted_at`, depois `entry_id`. Essa
ordem é estável em SQLite e PostgreSQL.

## Resposta e segurança

Valores `Decimal` são projetados explicitamente como strings, sem passagem por
`float`. Zeros não significativos introduzidos pela escala `Numeric` são
removidos apenas na apresentação, mantendo no mínimo duas casas:

```json
{
  "filters": {
    "collaborator_id": null,
    "start_date": null,
    "end_date": null
  },
  "credit_count": 1,
  "totals_by_currency": [{"currency": "BRL", "amount": "119.90"}],
  "items": [
    {
      "ledger_entry_id": "ledger.remuneration.credit:event-1",
      "commercial_event_id": "event-1",
      "collaborator_id": "collaborator-1",
      "amount": "119.90",
      "currency": "BRL",
      "entry_type": "credit"
    }
  ]
}
```

Snapshot vazio retorna `200`, `credit_count=0`, `totals_by_currency=[]` e
`items=[]`. Falhas inesperadas retornam `500` com mensagem fixa. DTOs HTTP não
expõem ORM, `raw_payload`, configuração, SQL ou traceback.

O handler global de validação diferencia a rota: ausência do upload continua
usando `upload_validation_error`, enquanto datas e query parameters inválidos
usam `invalid_query_parameters`. O intervalo invertido possui o código estável
`invalid_date_range`.

---

# 21. Resumo financeiro gerencial

`GetFinancialSummaryUseCase` projeta exclusivamente créditos persistidos no
Ledger. Ele não recebe fatos financeiros de entrada, não recalcula remuneração
e não persiste o resultado. A consulta abre uma única Unit of Work somente para
leitura e reutiliza `LedgerRepository.find_credits()`, que aplica no banco os
filtros opcionais de colaborador e datas.

Para o MVP, os créditos filtrados são agregados em memória na Application
Layer. A consulta carrega somente `LedgerEntry`, não busca eventos ou execuções,
não produz N+1 e mantém a infraestrutura simples. Views materializadas, tabelas
de resumo e cache permanecem fora do escopo.

## Agregação, ranking e percentuais

Cada par colaborador/moeda possui total e quantidade próprios. Moedas nunca são
somadas entre si. O ranking é sequencial e independente por moeda, aplicando:

1. maior valor agregado;
2. maior quantidade de créditos naquela moeda;
3. `collaborator_id` crescente.

Assim, até empates de valor têm posição estável. A lista externa de
colaboradores usa `collaborator_id` crescente e as moedas usam seu valor textual
crescente.

A participação é `valor do colaborador / total da moeda * 100`, calculada com
`Decimal` e arredondada para duas casas por `ROUND_HALF_UP`. Um total monetário
zero, embora impedido pelas restrições atuais dos créditos, possui projeção
segura de `0.00`. Dinheiro e percentuais são transportados como strings
decimais, sem `float`.

## Endpoint

```text
GET /financial/summary
GET /financial/summary?collaborator_id=collaborator-1
GET /financial/summary?start_date=2026-07-01&end_date=2026-07-31
```

Os filtros reutilizam `GetFinancialSnapshotQuery`: datas `YYYY-MM-DD`,
inclusivas sobre `posted_at` em UTC, sem janela temporal implícita. O endpoint
retorna `200` inclusive sem créditos, `422` para parâmetros inválidos e `500`
seguro para falhas inesperadas. A camada HTTP apenas constrói a query, executa o
serviço injetado pelo Composition Root e projeta DTOs explícitos.

O resumo atual não representa equipes, metas, folha de pagamento ou RV mensal.
Ele é somente uma visão gerencial dos créditos imutáveis já consolidados e
preserva a idempotência do Ledger em reimportações.

---

# 22. Auditoria de eventos comerciais

O drill-down fecha o fluxo gerencial sem duplicar o extrato financeiro:

```text
GET /financial/summary
        ↓
GET /financial/snapshot
        ↓
GET /commercial-events/{commercial_event_id}
```

`GetCommercialEventDetailsUseCase` recebe um identificador de até 128
caracteres, abre uma única Unit of Work e executa no máximo três consultas:
evento, lançamentos e execuções. Não chama o Rules Engine, não recalcula o
Financial Snapshot, não cria ProcessingRun e não chama `commit`.

## Modelo público

O evento expõe apenas `event_id`, `external_reference`, `source`,
`occurred_at`, `received_at` e `created_at`. `raw_payload` é deliberadamente
excluído do DTO de Application e do schema HTTP: ele pode conter dados pessoais,
acoplar consumidores ao transporte ou tornar o contrato instável.

Cada lançamento relacionado expõe sua identidade, tipo, beneficiário, valor,
moeda, instante, referências de postagem/cálculo/origem e fatura. A consulta usa
`LedgerRepository.find_by_event_id()` e inclui crédito, débito e ajuste,
ordenados por `posted_at` e `entry_id`. Dinheiro continua como `Decimal` na
Application e string decimal no HTTP.

Cada execução expõe identificador, status final, início, conclusão, versão das
regras e criação. Resultados internos de fase, warnings e estruturas JSON não
atravessam esta fronteira. As execuções são
ordenadas por `started_at` e `id`, tornando visíveis todas as tentativas
idempotentes.

Evento inexistente retorna `404` com `commercial_event_not_found`. Identificador
inválido retorna `422`; falhas inesperadas retornam `500` com mensagem fixa.
Nenhuma resposta inclui SQL, configuração, traceback, caminhos ou objetos ORM.

## Estrutura HTTP

Com o quinto endpoint, a rota e a projeção de eventos foram isoladas em
`api/commercial_events.py`; `app.py` permanece responsável pela criação da
aplicação e inclusão do router. `HttpApplicationServices` é uma dataclass
imutável de dependências explícitas, não um service locator.

A formatação decimal comum a snapshot, resumo e drill-down foi movida para
`api/projections.py`. A extração é pequena e específica para dinheiro, sem criar
uma biblioteca genérica de serialização.

O drill-down é somente leitura, sem edição, reprocessamento, raw payload,
autenticação ou integração MK.

---

# 23. Listagem de eventos comerciais

`ListCommercialEventsUseCase` permite localizar eventos persistidos antes de
existir crédito. Ele consulta exclusivamente `EventRepository.search()`, dentro
de uma Unit of Work de leitura, e não carrega LedgerEntries ou ProcessingRuns.
Não executa regras, não recalcula remuneração e não chama `commit`.

## Filtros e ordem

`source` e `external_reference` usam igualdade exata. `start_date` e `end_date`
são inclusivas sobre a data UTC de `occurred_at`; não existe período implícito.
A ordem fixa é:

1. `occurred_at` decrescente;
2. `event_id` decrescente.

Os filtros, a ordenação e o limite são aplicados pelo SQLAlchemy no banco.
Nesta versão o ORM materializa a entidade completa, inclusive `raw_payload`,
porque esse é o mapeamento existente. O caso de uso projeta imediatamente apenas
os seis campos públicos, e o payload nunca atravessa a Application ou o HTTP.
Uma projeção ORM paralela seria otimização prematura para o volume do MVP.

## Paginação keyset

O limite padrão é 50, com mínimo 1 e máximo 100. O caso de uso solicita
`limit + 1`; o registro excedente determina `has_more`, e a posição do último
item retornado forma o próximo cursor.

A posição tipada contém somente `occurred_at` e `event_id`. A camada HTTP
serializa JSON versionado e Base64 URL-safe; a Application não conhece JSON ou
Base64. O cursor não contém SQL, tabelas, filtros ou dados sensíveis e não
depende da existência posterior do evento que originou a posição.

Para a ordem descendente, a próxima página aplica:

```text
occurred_at < cursor.occurred_at
OR (
    occurred_at == cursor.occurred_at
    AND event_id < cursor.event_id
)
```

O consumidor deve repetir os mesmos filtros em todas as páginas. Cursor
inválido retorna `422` com `invalid_cursor`; resposta vazia retorna `200`.

## Fronteira HTTP

`GET /commercial-events` reutiliza `CommercialEventResponse`, preservando a
representação do drill-down. A lista não inclui raw payload, finanças, status
derivado, contagens ou resultados de processamento. Cada item pode ser aberto
em `GET /commercial-events/{commercial_event_id}`.

`api/pagination.py` concentra somente encode/decode do cursor e
`api/errors.py` concentra a pequena projeção estável de erros já usada pelas
rotas. Não foram criados framework de exceptions, OFFSET, `total_count`,
migration, cache ou tabela de resumo.

---

# 24. Linha do tempo financeira por colaborador

`GetCollaboratorFinancialTimelineUseCase` oferece uma visão cronológica dos
lançamentos persistidos de um beneficiário. Não existe entidade Collaborator
nesta etapa; um identificador válido sem lançamentos retorna `200` e lista
vazia.

O repositório executa uma única consulta por colunas entre `ledger_entries` e
`commercial_events`, vinculados pela foreign key `event_id`. A projeção retorna
somente campos necessários do Ledger e `event_id`, `external_reference`,
`source` e `occurred_at` do evento. Não materializa `raw_payload`, não consulta
ProcessingRuns e não produz N+1.

## Filtros, ordem e cursor

Datas são inclusivas sobre `posted_at` em UTC. `entry_type` e `currency` aceitam
somente os enums públicos existentes. A ordem fixa é:

1. `posted_at` decrescente;
2. `ledger_entry_id` decrescente.

O cursor próprio `CollaboratorFinancialTimelineCursorPosition` contém somente
`posted_at` e `ledger_entry_id`. A camada HTTP codifica JSON versionado em
Base64 URL-safe; ele não reutiliza o cursor de evento como identidade
financeira. A próxima página aplica a mesma comparação keyset descendente e o
caso de uso solicita `limit + 1`.

O limite padrão é 50, com mínimo 1 e máximo 100. Não há OFFSET, total global,
agregação ou período implícito.

## Navegação e segurança

O fluxo gerencial é:

```text
/financial/summary
    → /collaborators/{id}/financial-timeline
        → /commercial-events/{event_id}
```

Dinheiro permanece `Decimal` até `decimal_string()` na projeção HTTP. A timeline
não retorna raw payload, execuções, resultados de fases, status derivados ou
regras recalculadas. Falhas inesperadas usam mensagem fixa; cursor e filtros
inválidos retornam `422`.

`api/collaborators.py` contém exclusivamente transporte e projeção da timeline.
O serviço é uma dependência explícita de `HttpApplicationServices` e é montado
pelo Composition Root. Nenhuma migration ou modelo ORM persistido foi criado.

---

# 25. Drill-down de ProcessingRun

`GET /commercial-events/{id}` continua sendo o resumo das tentativas de um
evento. `GET /processing-runs/{processing_run_id}` abre uma tentativa específica
sem reexecutar o Rules Engine:

```text
/commercial-events/{event_id}
    → processing_run_id
        → /processing-runs/{processing_run_id}
```

`GetProcessingRunDetailsUseCase` usa uma única Unit of Work. Primeiro consulta
`ProcessingRunRepository.get_by_id()`; se existir, consulta o evento relacionado
por `EventRepository.get_by_id()`. São no máximo duas consultas, sem consulta
por fase, Ledger ou N+1. A foreign key torna evento órfão uma violação de
integridade, tratada como falha técnica segura.

## Contrato por allowlist

ProcessingRun persiste `phase_results`, `warnings` e `audit_references` em JSON.
As fases produzidas pela Application possuem `phase`, `status`, `can_continue`,
`warnings` e `audit_references`. A API expõe somente:

- `phase`;
- `status`;
- `can_continue`.

A ordem da lista persistida é preservada; fases não são ordenadas, deduplicadas
ou reconstruídas. `output`, warnings e referências não atravessam a fronteira,
pois as estruturas são livres e ainda não possuem garantia pública contra
conteúdo técnico ou sensível. Não há sanitização por regex.

O DTO da execução expõe identificadores, `final_status`, início, conclusão,
versão das regras e criação. O evento resumido expõe identificador, referência
externa, origem e ocorrência. Não são derivados duração, sucesso, causa raiz,
severidade ou recomendações.

## Segurança e composição

`api/processing_runs.py` recebe o ID, executa o serviço e projeta schemas
explícitos. O endpoint não retorna raw payload, JSON integral, traceback, SQL,
configuração, mensagens técnicas ou objetos ORM.

`ProcessingRunNotFound` é independente de HTTP e mapeado para `404`.
`processing_run_details` é dependência obrigatória de
`HttpApplicationServices`, construída pelo Composition Root. Consultas não
chamam `commit`, não criam execução e não alteram Ledger ou evento.

---

# 26. Saúde factual do processamento

`GET /processing/health` é uma visão operacional agregada dos dados
persistidos. Diferentemente de `GET /health`, que apenas confirma que o processo
HTTP está ativo e não acessa o banco, essa consulta abre uma Unit of Work de
leitura. Ela não atribui score, severidade, diagnóstico, taxa ou recomendação.

`GetProcessingHealthUseCase` recebe filtros tipados, delega a agregação à porta
`ProcessingHealthRepository` e devolve DTOs imutáveis. O Composition Root monta
`SqlAlchemyProcessingHealthRepository` na mesma Session da Unit of Work e
injeta o caso de uso em `HttpApplicationServices`. A rota
`api/processing.py` somente valida transporte, executa o serviço e projeta
schemas explícitos.

## Janela temporal e filtros

A referência temporal é exclusivamente `ProcessingRun.started_at`, com datas
inclusivas em UTC. `source` filtra a origem do CommercialEvent e
`rules_engine_version` filtra a versão persistida na execução.

Sem filtro de data ou versão, a coorte de eventos contém todos os eventos da
origem selecionada. Assim, eventos ainda sem execução permanecem visíveis.
Quando data ou versão é informada, a coorte passa a conter os eventos com ao
menos uma execução correspondente à janela; consequentemente, “eventos sem
execução” é zero nessa coorte. Essa política evita misturar silenciosamente
`occurred_at` do evento com `started_at` da execução. O cliente recebe os
filtros aplicados na resposta e nenhum período é presumido.

## Agregação e consistência

As contagens e os agrupamentos são executados no banco. Uma subconsulta de
execuções filtradas alimenta:

- total e `GROUP BY` de `final_status`;
- total e `GROUP BY` de `rules_engine_version`;
- contagem agregada de execuções por evento.

Outra subconsulta reduz o Ledger a um identificador por evento. A consulta de
eventos faz joins apenas com essas projeções agregadas, evitando que múltiplas
execuções combinadas com múltiplos lançamentos multipliquem contagens. O número
de consultas é constante, não há N+1 e nenhuma entidade completa, raw payload,
resultado de fase, warning, referência ou valor monetário é materializado.

Os agrupamentos são ordenados alfabeticamente pelo valor persistido. Totais de
execuções correspondem às somas por status e por versão, cujas colunas são
obrigatórias no modelo atual. Eventos sem Ledger não são classificados como
erro, e eventos com várias execuções não são classificados como duplicados.

## Segurança e limites

A operação não chama `commit`, não recalcula regras e não cria registros.
Filtros inválidos retornam `422`; falhas inesperadas usam mensagem fixa e não
expõem SQL, ORM, credenciais, caminhos ou exceções. A primeira versão não
fornece percentuais, duração, tendências, séries temporais, thresholds nem
listas de itens. O drill-down permanece nos endpoints de CommercialEvent e
ProcessingRun.
