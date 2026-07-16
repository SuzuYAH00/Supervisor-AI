# Integrações do Supervisor AI

## 1. Objetivo

Este documento descreve os sistemas externos que fornecem informações ao Supervisor AI.

O Supervisor AI não substitui os sistemas existentes. Ele atua como uma camada de integração, processamento e inteligência, utilizando dados originados nas ferramentas já utilizadas pela empresa.

---

# 2. Visão geral das integrações

As principais fontes de dados identificadas são:

| Sistema | Responsabilidade |
|---|---|
| MK Solutions | Operação, clientes, tickets, financeiro e contratos |
| NPX | Ligações, atendimentos e registros de ponto |
| MKBot | Atendimentos via WhatsApp e CSAT |
| Colabore | Controle de ponto e ausências |
| AppSheet | Registro de horas extras |
| Google Sheets | Bases manuais e consolidações atuais |
| Looker Studio | Visualização atual dos indicadores |

---

# 3. MK Solutions

## Descrição

O MK Solutions é atualmente uma das principais fontes operacionais da empresa.

Ele concentra informações relacionadas aos clientes, contratos, atendimentos e processos internos.

---

## Módulos utilizados

### CRM

Responsável por gestão comercial.

Uso atual:

- Abertura de leads para clientes interessados em câmeras.

Importância:

Baixa.

---

### Financeiro

Responsável pelas informações financeiras.

Uso atual:

- Verificação de pagamentos;
- Análise de inadimplência;
- Consulta de contratos;
- Relatórios de cancelamentos.

Importância:

Alta.

---

### Workspace

Responsável pelos processos operacionais.

Uso atual:

- Abertura de tickets;
- Acompanhamento;
- Encerramento;
- Consulta cadastral;
- Histórico operacional.

Importância:

Muito alta.

---

### Técnico

Responsável pelas informações técnicas.

Uso atual:

- Status de conexão;
- Clientes online/offline;
- Histórico de sessões;
- Ferramentas técnicas.

Importância:

Alta.

---

### Integradores

Responsável por integrações externas.

Uso atual:

- Processos específicos;
- Informações relacionadas ao Watch em cancelamentos.

Importância:

Baixa.

---

### Maps

Responsável por geolocalização.

Uso atual:

- Viabilidade de mudança de endereço.

Importância:

Baixa.

---

### Bot

Responsável pelo atendimento automatizado.

Uso atual:

- Atendimento via WhatsApp;
- Histórico de conversas;
- Coleta de CSAT;
- Exportação de atendimentos.

Importância:

Muito alta.

---

# 4. NPX

## Descrição

Sistema utilizado para atendimento via ligação e controle de algumas informações operacionais.

---

## Dados utilizados

- Atendimentos realizados;
- Avaliações de satisfação;
- Identificação do operador;
- Registro de ponto.

---

## Processos relacionados

- CSAT;
- Indicadores;
- RV;
- Atrasos.

---

# 5. MKBot

## Descrição

Sistema responsável pelos atendimentos realizados via WhatsApp.

---

## Dados utilizados

- Histórico de conversas;
- Atendimento;
- Operador;
- Avaliação do cliente;
- CSAT.

---

## Observações

O atendimento permanece disponível por aproximadamente 70 dias para consulta.

A avaliação pode ocorrer até 30 minutos após o encerramento da conversa.

---

# 6. Colabore

## Descrição

Sistema utilizado para controle de jornada.

---

## Dados utilizados

- Entrada;
- Saída;
- Intervalos;
- Ausências;
- Atrasos.

---

## Processos relacionados

- RV;
- Extras;
- Assiduidade.

---

# 7. AppSheet

## Descrição

Sistema utilizado atualmente para registro das horas extras realizadas.

---

## Dados utilizados

- Data da extra;
- Horário inicial;
- Horário final;
- Intervalo;
- Motivo;
- Tipo de extra.

---

## Validações necessárias

O Supervisor AI deve comparar:

AppSheet

versus

Colabore

Para identificar conflitos de horário.

Exemplo:

Extra registrada:

08:00 - 14:00

Ponto:

13:50 - 20:00

Resultado:

Extra inválida por sobreposição.

---

# 8. Google Sheets

## Descrição

Atualmente representa uma camada intermediária de armazenamento e cálculo.

---

## Utilização atual

- Upgrade;
- RV;
- Extras;
- Indicadores;
- Consolidação de pagamentos.

---

## Evolução esperada

O Supervisor AI deve reduzir gradualmente a dependência dessas planilhas, substituindo processos manuais por coleta e processamento automatizado.

---

# 9. Looker Studio

## Descrição

Ferramenta atualmente utilizada para visualização dos indicadores.

---

## Uso atual

Após tratamento dos dados:

Planilhas

↓

Looker Studio

↓

Dashboard

---

## Evolução esperada

O Supervisor AI deverá possuir sua própria camada de visualização, podendo utilizar dashboards próprios.

---

# 10. Estratégia futura de integração

A arquitetura futura deve seguir o fluxo:

```
Sistemas externos

↓

Camada de coleta

↓

Processamento

↓

Banco de dados

↓

Regras de negócio

↓

Inteligência artificial

↓

Interface Supervisor AI
```

---

# 11. Observações

As integrações podem evoluir conforme a disponibilidade de APIs, permissões de acesso e limitações dos sistemas atuais.

A primeira versão do Supervisor AI deve priorizar integrações que impactam diretamente:

- Pagamentos;
- Indicadores;
- Desempenho;
- Tomada de decisão da supervisão.
