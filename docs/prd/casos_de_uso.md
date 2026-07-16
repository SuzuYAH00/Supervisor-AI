# Casos de Uso - Supervisor AI

## Objetivo

Este documento descreve as principais funcionalidades esperadas do Supervisor AI sob a perspectiva do usuário.

Os casos de uso representam ações reais realizadas pelos supervisores e gestores durante a operação.

Cada caso de uso poderá originar uma ou mais funcionalidades do sistema.

---

# UC-001 - Visualizar resumo da operação

## Objetivo

Permitir que o supervisor compreenda rapidamente a situação atual da operação.

## Atores

- Supervisor
- Gerente

## Fluxo

1. Usuário acessa o sistema.
2. O sistema apresenta o Dashboard.
3. São exibidos os principais indicadores.
4. O sistema apresenta alertas relevantes.

## Resultado esperado

O supervisor consegue definir suas prioridades em poucos minutos.

---

# UC-002 - Consultar desempenho de um colaborador

## Objetivo

Permitir uma análise individual do desempenho.

## Informações

- CSAT
- Reincidência
- Qualidade
- Upgrades
- Extras
- Pagamentos
- Evolução

---

# UC-003 - Consultar pagamentos

## Objetivo

Permitir visualizar quanto cada colaborador receberá.

Informações:

- Upgrade
- RV
- Extras
- Total

---

# UC-004 - Acompanhar upgrades

## Objetivo

Permitir acompanhar todo o ciclo de um upgrade.

Fluxo esperado:

Cliente altera plano

↓

Supervisor AI identifica alteração

↓

Verifica pagamento

↓

Calcula premiação

↓

Disponibiliza para pagamento

---

# UC-005 - Validar horas extras

## Objetivo

Automatizar a conferência das extras.

Validações:

- Sobreposição de horários
- Jornada existente
- Intervalo
- Tipo de extra
- Situação

---

# UC-006 - Consultar indicadores

Permitir acompanhar:

- CSAT
- Reincidência
- Qualidade
- Cancelamentos
- Upgrades
- Extras

Filtros:

- Período
- Equipe
- Colaborador

---

# UC-007 - Identificar operadores abaixo da média

Objetivo:

Encontrar rapidamente colaboradores que necessitam acompanhamento.

O sistema deverá destacar automaticamente:

- Queda de desempenho
- Tendências negativas
- Indicadores críticos

---

# UC-008 - Identificar destaques positivos

Objetivo

Facilitar reconhecimento.

Exemplos:

- Melhor CSAT
- Maior evolução
- Mais upgrades
- Melhor qualidade

---

# UC-009 - Consultar análise de cancelamentos

Objetivo

Permitir análise dos cancelamentos.

Informações:

- Motivos
- Tendências
- Frequência
- Comparativos

---

# UC-010 - Gerar relatório de cancelamentos

Objetivo

Automatizar a geração do relatório mensal.

O relatório deverá apresentar:

- Indicadores
- Motivos
- Padrões encontrados
- Evidências
- Conclusões

---

# UC-011 - Consultar reincidências

Objetivo

Permitir analisar reincidências.

Informações:

- Cliente
- Operador
- Atendimento original
- Atendimento reincidente
- Dias entre atendimentos

---

# UC-012 - Consultar alertas

Objetivo

Apresentar problemas automaticamente.

Exemplos:

- CSAT em queda
- Cancelamentos aumentando
- Operador abaixo da média
- Upgrades aguardando pagamento

---

# UC-013 - Conversar com a IA

Objetivo

Permitir consultas em linguagem natural.

Exemplos:

"Quem precisa de feedback?"

"Qual foi o principal motivo de cancelamento?"

"Quem vendeu mais upgrades?"

"Quais indicadores pioraram?"

---

# UC-014 - Consultar histórico

Objetivo

Permitir visualizar evolução histórica.

Exemplos:

- Colaborador
- Equipe
- Indicador
- Pagamentos

---

# UC-015 - Comparar períodos

Objetivo

Comparar desempenho entre períodos.

Exemplos:

- Semana atual × anterior
- Mês atual × anterior
- Equipe A × Equipe B

---

# UC-016 - Planejar férias

Objetivo

Auxiliar o supervisor na organização da equipe.

Informações:

- Colaboradores elegíveis
- Impacto operacional
- Necessidade de cobertura

---

# UC-017 - Planejar extras

Objetivo

Auxiliar na distribuição de horas extras.

O sistema deverá considerar:

- Escala
- Disponibilidade
- Prioridades
- Histórico

---

# UC-018 - Gerar recomendações

Objetivo

Permitir que a IA identifique oportunidades automaticamente.

Exemplos:

- Necessidade de treinamento
- Mudança no pós-venda
- Aumento de cancelamentos
- Operadores com evolução positiva

---

# UC-019 - Consultar dashboards

Objetivo

Disponibilizar dashboards atualizados automaticamente.

Sem necessidade de atualização manual.

---

# UC-020 - Administrar parâmetros

Objetivo

Permitir configuração das regras do sistema.

Exemplos:

- Valores da RV
- Metas
- Limites
- Permissões

---

# Evolução dos casos de uso

Cada caso de uso poderá ser detalhado futuramente com:

- Fluxo principal
- Fluxos alternativos
- Regras de negócio
- Protótipos
- APIs
- Banco de dados
- Critérios de aceite

Este documento representa apenas a visão funcional inicial do Supervisor AI.
