# Banco de Dados

## Objetivo

Definir a estrutura lógica do banco de dados do Supervisor AI.

O banco não tem como objetivo substituir os sistemas da empresa (MK Solutions, NPX, Colabore, AppSheet etc.), mas atuar como uma camada centralizadora de informações.

Seu papel é:

- Centralizar dados provenientes de múltiplas fontes;
- Aplicar regras de negócio;
- Consolidar indicadores;
- Disponibilizar informações para dashboards, IA e relatórios.

---

# Princípios

O banco deve seguir os seguintes princípios.

## Fonte de verdade

Sempre que possível, a fonte oficial continuará sendo o sistema de origem.

Exemplos:

- Clientes → MK
- Tickets → MK
- Financeiro → MK
- Ligações → NPX
- Ponto → Colabore

O Supervisor AI armazenará apenas os dados necessários para processamento e histórico.

---

## Baixo acoplamento

As tabelas não devem depender diretamente da estrutura interna dos sistemas externos.

Cada integração será responsável por traduzir os dados recebidos para o modelo interno do Supervisor AI.

---

## Escalabilidade

Novos módulos poderão ser adicionados futuramente sem necessidade de remodelar todo o banco.

---

# Domínios do banco

O banco será organizado por domínios de negócio.

```
Autenticação

Operação

Clientes

Atendimentos

Financeiro

Indicadores

Integrações

Alertas
```

---

# Estrutura inicial

## usuarios

Responsável pela autenticação.

Principais informações:

- id
- nome
- email
- senha_hash
- perfil
- ativo

---

## colaboradores

Representa os colaboradores da empresa.

Principais informações:

- id
- código interno
- nome
- cargo
- equipe
- setor
- status

---

## clientes

Representa clientes importados do MK.

Principais informações:

- id interno
- código MK
- nome
- plano atual
- status

---

## planos

Catálogo de planos encontrados no MK.

Importante:

Esta tabela **não será fixa**.

Sempre que um novo plano aparecer durante as importações, ele será cadastrado automaticamente.

Isso elimina qualquer dependência de valores previamente documentados.

---

## tickets

Representa qualquer ticket operacional.

Exemplos:

- Atendimento
- Upgrade
- Cancelamento
- Suporte

Campos principais:

- protocolo
- cliente
- colaborador
- abertura
- encerramento
- origem

---

## atendimentos

Representa cada atendimento realizado.

Origens:

- NPX
- MKBot

Informações:

- identificador externo
- colaborador
- cliente
- canal
- início
- fim
- avaliação

---

## upgrades

Representa alterações de plano.

Informações:

- ticket
- cliente
- plano anterior
- plano novo
- data
- pagamento confirmado
- premiado
- competência

---

## indicadores

Tabela responsável por armazenar indicadores consolidados.

Exemplos:

- CSAT
- Qualidade
- Reincidência
- Cancelamentos
- Upgrades

Cada registro conterá:

- indicador
- colaborador
- período
- valor

Novos indicadores poderão ser adicionados sem alterações estruturais.

---

## rv

Resultado consolidado da renda variável.

Informações:

- colaborador
- período
- créditos
- débitos
- valor final
- situação

---

## extras

Representa horas extras aprovadas.

Informações:

- colaborador
- data
- início
- fim
- intervalo
- percentual
- validada
- paga

---

## importacoes

Responsável pelo controle de sincronizações.

Campos principais:

- sistema
- data
- início
- fim
- registros importados
- registros atualizados
- erros encontrados
- status

Essa tabela permitirá auditoria completa das integrações.

---

## alertas

Representa alertas gerados automaticamente.

Exemplos:

- Operador abaixo da média
- Queda de CSAT
- Cancelamentos acima do esperado
- Upgrade aguardando pagamento

Cada alerta possuirá:

- tipo
- prioridade
- origem
- colaborador
- descrição
- status

---

# Relacionamentos

```
Usuários
        │
        ▼
Colaboradores
        │
        ├──────────────┐
        ▼              ▼
Atendimentos      Upgrades
        │              │
        └──────┬───────┘
               ▼
           Indicadores
               │
               ▼
              RV

Clientes
    │
    ▼
 Planos

Importações

Alertas
```

---

# Arquitetura das integrações

O Supervisor AI utilizará um modelo baseado em conectores.

```
MK
      \
NPX ----\
          \
Colabore ---> Motor de Importação
          /
AppSheet /
        /

↓

Banco de Dados

↓

Processamento

↓

Regras de Negócio

↓

Dashboard

↓

IA
```

Cada sistema possuirá apenas um conector responsável por traduzir seus dados.

Todo o restante do processamento será realizado pelo Supervisor AI.

Essa arquitetura evita duplicação de código e facilita a inclusão de novas integrações futuramente.

---

# O que NÃO fará parte do MVP

Os seguintes domínios não serão implementados na primeira versão:

- Gestão de férias
- Gestão documental
- Controle de reuniões
- Gestão de treinamentos
- Sistema de metas
- Configurações avançadas
- Controle granular de permissões
- Auditoria completa
- Histórico de conversas da IA

Esses módulos serão adicionados conforme a evolução do produto.

---

# Evolução futura

A estrutura proposta foi planejada para permitir que o Supervisor AI evolua de um sistema interno para uma plataforma de inteligência operacional.

Novos módulos deverão reutilizar os mesmos princípios:

- Importação por conectores;
- Processamento centralizado;
- Regras de negócio independentes;
- Banco desacoplado dos sistemas externos;
- IA utilizando uma única base consolidada de informações.
