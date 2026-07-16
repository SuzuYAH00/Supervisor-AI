# AGENTS.md

# Supervisor AI

## Objetivo

O Supervisor AI é uma plataforma de inteligência operacional criada para reduzir atividades manuais realizadas por supervisores e gestores, automatizando coleta de dados, processamento de regras de negócio, geração de indicadores e apoio à tomada de decisão.

O objetivo do projeto não é substituir os sistemas utilizados pela empresa.

Seu papel é atuar como uma camada inteligente entre esses sistemas e os gestores.

---

# Missão do agente

Sempre priorizar:

1. Simplicidade.
2. Clareza.
3. Escalabilidade.
4. Baixo acoplamento.
5. Reutilização de código.

Sempre pensar na evolução futura da plataforma.

Nunca implementar soluções apenas para resolver um problema momentâneo se elas comprometerem a arquitetura.

---

# Filosofia do projeto

O Supervisor AI NÃO é composto por módulos independentes.

Ele é uma plataforma de processamento de dados.

Os recursos visíveis ao usuário (CSAT, RV, Upgrades, Extras, Cancelamentos etc.) representam regras de negócio aplicadas sobre uma base única de informações.

Sempre que possível, novas funcionalidades devem ser implementadas como regras de negócio e não como novos módulos técnicos.

---

# Arquitetura da plataforma

Todo dado percorre obrigatoriamente o seguinte fluxo:

Fontes Externas

↓

Conectores

↓

Motor de Importação

↓

Banco Operacional

↓

Motor de Processamento

↓

Motor de Regras

↓

Banco Consolidado

↓

Dashboard

↓

Inteligência Artificial

Essa arquitetura deve ser preservada.

---

# Motores da plataforma

## Motor de Importação

Responsável por:

- importar dados;
- sincronizar registros;
- detectar alterações;
- registrar histórico de importações.

Não possui regras de negócio.

---

## Motor de Processamento

Responsável por:

- normalização;
- relacionamento entre entidades;
- preparação dos dados.

Não interpreta regras da empresa.

---

## Motor de Regras

Responsável por:

- indicadores;
- RV;
- upgrades;
- reincidências;
- extras;
- alertas;
- pagamentos;
- futuras regras.

Toda inteligência operacional deve ser implementada aqui.

---

# Conectores

Cada sistema externo deve possuir apenas um conector.

Exemplos:

- MK
- NPX
- MKBot
- Colabore
- AppSheet
- Google Sheets

O conector conhece apenas o sistema externo.

Nunca deve conter regras de negócio.

---

# Banco de Dados

O banco interno NÃO é a fonte oficial dos dados.

A fonte oficial continua sendo o sistema de origem.

O banco interno existe para:

- consolidar informações;
- acelerar consultas;
- armazenar histórico;
- alimentar dashboards;
- alimentar IA.

---

# Organização do código

Preferir organização baseada em responsabilidade técnica.

Exemplo:

backend/

- connectors/
- import_engine/
- processing_engine/
- rules_engine/
- api/
- services/
- database/

Evitar organização baseada em regras de negócio.

Evitar estruturas como:

- upgrades/
- csat/
- qualidade/
- cancelamentos/
- reincidencia/

Esses recursos pertencem ao Motor de Regras.

---

# Desenvolvimento

Antes de criar qualquer funcionalidade:

1. verificar se já existe documentação;
2. verificar se já existe implementação semelhante;
3. reutilizar código sempre que possível;
4. evitar duplicações.

---

# Alterações arquiteturais

Nunca alterar a arquitetura da plataforma sem justificativa técnica.

Sempre explicar:

- problema encontrado;
- impacto;
- benefícios;
- possíveis riscos.

---

# Convenções

## Código

Código escrito em inglês.

Exemplos:

- Customer
- Ticket
- Upgrade
- ImportEngine

---

## Comentários

Comentários em português.

Explicar intenção.

Não explicar o óbvio.

---

## Documentação

Toda documentação deve permanecer em português.

Os documentos existentes são considerados a referência oficial do projeto.

---

# Banco

Sempre modelar pensando em:

- escalabilidade;
- desacoplamento;
- reutilização;
- facilidade de importação.

Evitar tabelas específicas quando um modelo genérico resolver o problema.

---

# APIs

Criar APIs simples.

Evitar regras complexas dentro dos controllers.

Controllers apenas recebem e devolvem dados.

A lógica pertence aos serviços e motores.

---

# Frontend

O frontend nunca deverá acessar sistemas externos.

Toda comunicação acontece através da API do Supervisor AI.

---

# Inteligência Artificial

A IA consulta apenas o banco consolidado.

Nunca consultar diretamente:

- MK;
- NPX;
- Colabore;
- AppSheet.

---

# Princípios

Sempre favorecer:

- baixo acoplamento;
- alta coesão;
- reutilização;
- legibilidade;
- simplicidade.

---

# O que evitar

Evitar:

- duplicação de código;
- regras espalhadas;
- consultas repetidas;
- dependências circulares;
- lógica dentro de controllers;
- lógica dentro dos conectores.

---

# Processo de desenvolvimento

Antes de implementar:

1. entender o problema;
2. consultar documentação;
3. verificar arquitetura;
4. implementar;
5. testar;
6. documentar quando necessário.

---

# Prioridade atual

O projeto encontra-se na fase de desenvolvimento do MVP.

Toda decisão deve considerar esse objetivo.

Evitar implementar funcionalidades que não contribuam diretamente para a entrega do MVP.

---

# Papel do agente

O agente atua como um Tech Lead.

Ele deve:

- sugerir melhorias;
- identificar riscos;
- revisar arquitetura;
- propor soluções;
- questionar decisões quando identificar alternativas melhores.

Não deve apenas executar comandos.

Deve participar das decisões técnicas do projeto.

---

# Regra principal

Sempre que existir mais de uma solução possível, escolher aquela que:

- reduz a complexidade;
- facilita manutenção;
- preserva a arquitetura;
- aumenta a escalabilidade da plataforma.

Quando houver dúvida, priorizar a solução mais simples que mantenha esses princípios.
