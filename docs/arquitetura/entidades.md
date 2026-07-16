# Entidades do Supervisor AI

## 1. Objetivo

Este documento define as principais entidades existentes dentro do Supervisor AI.

As entidades representam os objetos que o sistema precisa compreender para realizar coleta de dados, aplicar regras de negócio, gerar análises e auxiliar gestores na tomada de decisão.

As entidades são divididas em:

- Entidades de negócio: representam elementos reais da operação.
- Entidades de sistema: representam elementos necessários para funcionamento da plataforma.

---

# 2. Entidades de negócio

---

# Colaborador

Representa um funcionário da operação.

É uma das principais entidades do sistema, pois grande parte das análises e pagamentos são relacionadas ao desempenho individual.

## Informações principais

- Identificador único
- Nome
- Função
- Equipe
- Turno
- Supervisor responsável
- Status

## Relacionamentos

Um colaborador pode:

- Realizar atendimentos;
- Gerar upgrades;
- Realizar horas extras;
- Possuir indicadores;
- Receber pagamentos;
- Receber alertas de desempenho.

---

# Cliente

Representa um cliente cadastrado na empresa.

## Fonte principal

MK Solutions

## Informações principais

- Código do cliente
- Nome
- Plano atual
- Valor do plano
- Status do contrato
- Data de instalação
- Histórico financeiro

## Relacionamentos

Um cliente pode:

- Possuir contratos;
- Realizar atendimentos;
- Solicitar upgrades;
- Gerar cancelamentos;
- Gerar reincidências.

---

# Contrato

Representa o vínculo comercial entre cliente e empresa.

## Informações principais

- Cliente relacionado
- Plano contratado
- Valor mensal
- Data de início
- Status
- Fidelidade

## Relacionamentos

Um contrato pertence a um cliente e pode sofrer alterações através de upgrades ou cancelamentos.

---

# Atendimento

Representa um contato realizado pelo cliente.

Pode ocorrer através de:

- Ligação;
- WhatsApp.

## Fontes

- NPX
- MKBot

## Informações principais

- Identificador único
- Cliente
- Operador responsável
- Canal
- Data e horário
- Processo
- Classificação de abertura
- Classificação de encerramento
- Nota CSAT

## Relacionamentos

Um atendimento:

- Pertence a um cliente;
- É realizado por um colaborador;
- Pode gerar ticket;
- Pode gerar reincidência;
- Pode gerar indicadores.

---

# Ticket

Representa um registro operacional dentro do MK Workspace.

## Fonte

MK Workspace

## Informações principais

- Protocolo
- Cliente
- Operador
- Tipo de solicitação
- Data
- Status

## Exemplos

- Mudança de plano;
- Cancelamento;
- Atendimento;
- Visita técnica.

## Relacionamentos

Um ticket pode estar relacionado a:

- Cliente;
- Atendimento;
- Upgrade;
- Cancelamento.

---

# Upgrade

Representa uma alteração comercial que aumenta o faturamento do cliente.

## Fonte

MK Workspace

## Informações principais

- Cliente
- Operador responsável
- Protocolo
- Plano anterior
- Novo plano
- Valor anterior
- Novo valor
- Data da alteração
- Status do pagamento

## Estados

- Identificado;
- Plano alterado;
- Cliente pagou;
- Pago ao colaborador.

## Relacionamentos

Um upgrade:

- Pertence a um cliente;
- É realizado por um colaborador;
- Está relacionado a um ticket;
- Pode gerar pagamento.

---

# Cancelamento

Representa a saída de um cliente da empresa.

## Fonte

MK Financeiro / MK Solutions

## Informações principais

- Cliente
- Data do cancelamento
- Motivo
- Tempo de contrato
- Histórico de atendimento
- Responsável pelo atendimento

## Relacionamentos

Um cancelamento:

- Pertence a um cliente;
- Pode estar relacionado a atendimentos anteriores;
- Pode gerar análises de padrão.

---

# Extra

Representa uma jornada de trabalho adicional realizada por um colaborador.

## Fontes

- AppSheet
- Colabore
- NPX

## Informações principais

- Colaborador
- Data
- Horário inicial
- Horário final
- Intervalo
- Tipo de extra
- Motivo
- Status de validação

## Relacionamentos

Uma extra:

- Pertence a um colaborador;
- Possui validação;
- Gera pagamento.

---

# Indicador

Representa uma métrica utilizada para avaliação operacional.

## Exemplos

- CSAT;
- Reincidência;
- Qualidade;
- Upgrade;
- Cancelamentos;
- Atrasos.

## Informações principais

- Nome
- Valor
- Período
- Colaborador relacionado
- Equipe
- Fonte dos dados

## Relacionamentos

Um indicador pode:

- Influenciar RV;
- Gerar alerta;
- Aparecer em dashboards.

---

# RV

Representa a renda variável do colaborador.

## Componentes

Critérios positivos:

- CSAT;
- Reincidência;
- Qualidade.

Critérios negativos:

- Atrasos;
- Ausências.

## Informações principais

- Colaborador
- Período
- Créditos
- Débitos
- Resultado final

## Relacionamentos

Uma RV:

- Pertence a um colaborador;
- É calculada através de indicadores;
- Gera pagamento.

---

# Pagamento

Representa valores financeiros destinados ao colaborador.

## Tipos

- Upgrade;
- RV;
- Extra.

## Informações principais

- Colaborador
- Tipo
- Valor
- Período
- Status

## Relacionamentos

Um pagamento:

- Pertence a um colaborador;
- É originado por uma regra de negócio.

---

# 3. Entidades de sistema

---

# Usuário

Representa uma pessoa que acessa o Supervisor AI.

## Exemplos

- Supervisor;
- Gerente;
- Administrador.

## Informações

- Nome
- Permissões
- Perfil de acesso

---

# Fonte de Dados

Representa sistemas externos conectados ao Supervisor AI.

## Exemplos

- MK Solutions;
- NPX;
- MKBot;
- Colabore;
- AppSheet.

## Informações

- Nome
- Tipo
- Última sincronização
- Status da integração

---

# Importação

Representa uma coleta realizada de uma fonte externa.

## Informações

- Fonte
- Data
- Quantidade de registros
- Status
- Erros encontrados

---

# Alerta

Representa uma informação gerada automaticamente pelo sistema.

## Exemplos

- Indicador abaixo da média;
- Aumento de cancelamentos;
- Queda de CSAT;
- Meta próxima.

## Informações

- Tipo
- Data
- Severidade
- Entidade relacionada
- Status

---

# Histórico

Representa alterações e eventos importantes realizados no sistema.

## Exemplos

- Atualização de indicador;
- Mudança de regra;
- Pagamento realizado.

---

# 4. Relacionamentos principais

```
Colaborador
    |
    ├── realiza Atendimento
    |
    ├── gera Upgrade
    |
    ├── realiza Extra
    |
    ├── possui RV
    |
    └── recebe Pagamento


Cliente
    |
    ├── possui Contrato
    |
    ├── possui Atendimento
    |
    ├── pode gerar Upgrade
    |
    └── pode gerar Cancelamento


Atendimento
    |
    ├── pode gerar Ticket
    |
    ├── pode gerar Reincidência
    |
    └── possui CSAT


Indicadores
    |
    └── alimentam RV e Alertas
```

---

# 5. Observação

Este documento representa a visão inicial das entidades do Supervisor AI.

Durante a evolução do desenvolvimento, novas entidades podem surgir ou entidades existentes podem ser divididas conforme necessidade técnica e de negócio.
