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
