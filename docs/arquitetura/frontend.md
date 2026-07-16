# Arquitetura Frontend do Supervisor AI

## 1. Objetivo

O frontend do Supervisor AI será a camada de interação entre os gestores e as informações processadas pelo sistema.

Seu objetivo principal é transformar dados operacionais em uma experiência simples, rápida e orientada à tomada de decisão.

O frontend não deve apenas exibir informações, mas ajudar o supervisor a responder perguntas importantes da operação.

Exemplos:

- O que precisa da minha atenção hoje?
- Quem está abaixo da média?
- Qual problema está aumentando?
- Qual ação devo tomar?

---

# 2. Princípios da interface

## Informação antes de complexidade

A interface deve priorizar informações relevantes.

O supervisor não deve precisar navegar por várias telas para encontrar problemas importantes.

---

## Decisão rápida

A primeira tela deve permitir uma compreensão rápida da operação.

Objetivo:

"Em 30 segundos, entender como a equipe está."

---

## Dados antes de opiniões

Todas as recomendações devem possuir origem em dados.

Exemplo:

Não informar:

"João precisa melhorar."

Informar:

"João apresentou CSAT 0,4 abaixo da média da equipe nos últimos 7 dias."

---

# 3. Estrutura inicial de telas

## Dashboard principal

Tela inicial do supervisor.

Objetivo:

Apresentar a situação atual da operação.

Informações possíveis:

- Indicadores gerais;
- Alertas;
- Evolução recente;
- Pendências;
- Destaques positivos.

---

# 4. Módulo de indicadores

Responsável por acompanhar métricas operacionais.

Indicadores:

- CSAT;
- Reincidência;
- Qualidade;
- Cancelamentos;
- Upgrades;
- Extras.

Possibilidades:

- Filtrar por período;
- Filtrar por equipe;
- Filtrar por colaborador;
- Comparar evolução.

---

# 5. Módulo de colaboradores

Responsável pela análise individual.

Informações:

- Nome;
- Equipe;
- Indicadores atuais;
- Histórico;
- Pontos positivos;
- Pontos de atenção.

Exemplo:

```
Colaborador: João

CSAT:
Atual: 9,4
Média equipe: 9,7

Reincidência:
Atual: 12%
Média equipe: 8%

Sugestão:
Avaliar atendimentos técnicos recentes.
```

---

# 6. Módulo de pagamentos

Responsável por acompanhar valores destinados aos colaboradores.

Exibir:

- Upgrade;
- RV;
- Extras;
- Total.

Exemplo:

```
João

Upgrade:
R$ 299,90

RV:
R$ 400,00

Extras:
R$ 180,00

Total:
R$ 879,90
```

---

# 7. Módulo de upgrades

Responsável pelo acompanhamento das vendas realizadas.

Informações:

- Cliente;
- Operador;
- Plano anterior;
- Novo plano;
- Valor;
- Status.

Estados:

- Alteração pendente;
- Cliente aguardando pagamento;
- Pago;
- Finalizado.

---

# 8. Módulo de extras

Responsável pelo acompanhamento das horas extras.

Informações:

- Colaborador;
- Data;
- Horário;
- Tipo;
- Valor;
- Validação.

Validações:

- Conflito com jornada;
- Intervalo;
- Aprovação.

---

# 9. Módulo de cancelamentos

Responsável por análise de perda de clientes.

Informações:

- Quantidade;
- Motivos;
- Padrões encontrados;
- Clientes recentes;
- Tendências.

Objetivo:

Encontrar causas e oportunidades de melhoria.

---

# 10. Central de alertas

Uma das principais funções do Supervisor AI.

Exemplos:

## Alerta de desempenho

"Operador abaixo da média de CSAT há 7 dias."

---

## Alerta operacional

"Quantidade de cancelamentos aumentou 20% comparado ao período anterior."

---

## Alerta financeiro

"Existem upgrades aguardando confirmação de pagamento."

---

# 11. Assistente de inteligência artificial

O frontend deverá possuir uma área onde o supervisor possa conversar com a IA.

Exemplos:

Pergunta:

"Qual foi o principal motivo de cancelamento esse mês?"

Resposta:

"A principal causa foi inadimplência, representando X% dos cancelamentos analisados."

---

Pergunta:

"Quem precisa de acompanhamento?"

Resposta:

"3 colaboradores apresentam queda de desempenho comparado à média da equipe."

---

# 12. Perfis de acesso

## Supervisor

Visualização:

- Sua equipe;
- Seus indicadores;
- Seus pagamentos.

---

## Gerente

Visualização:

- Todas as equipes;
- Comparações;
- Relatórios gerais.

---

## Administrador

Visualização:

- Configurações;
- Usuários;
- Parâmetros.

---

# 13. Evolução futura

Possíveis evoluções:

- Aplicativo mobile;
- Notificações;
- Dashboards personalizados;
- Recomendações automáticas;
- Ações executadas pela IA.

---

# 14. Observação

A primeira versão do frontend deve priorizar simplicidade.

O objetivo inicial não é criar uma ferramenta complexa, mas entregar uma visão operacional rápida e confiável para o supervisor.
