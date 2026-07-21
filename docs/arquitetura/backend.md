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
