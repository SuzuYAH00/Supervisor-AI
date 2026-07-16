# PROJECT_CONTEXT.md

# Supervisor AI

## Contexto do Projeto

Este documento reúne o conhecimento operacional adquirido durante a fase de levantamento de requisitos.

Seu objetivo é fornecer contexto para qualquer desenvolvedor ou agente de IA que participe do projeto.

A arquitetura está documentada em `/docs/arquitetura`.

Este documento descreve o negócio.

---

# O que é o Supervisor AI?

O Supervisor AI é uma plataforma de inteligência operacional.

Seu objetivo é eliminar processos manuais realizados por supervisores através da centralização de dados, automação de cálculos, geração de indicadores e suporte à tomada de decisão.

O sistema atua entre os sistemas utilizados pela empresa e seus gestores.

Ele não substitui os sistemas existentes.

---

# Problema atual

Hoje a operação depende de diversos sistemas independentes.

Principais exemplos:

- MK Solutions
- NPX
- MKBot
- Colabore
- Google Sheets
- Looker Studio
- AppSheet

Grande parte das atividades depende de:

- exportações;
- filtros;
- planilhas;
- consolidação manual;
- conferências repetitivas.

Esses processos consomem tempo e aumentam a possibilidade de erros.

---

# Filosofia da operação

A gestão trabalha baseada em dados.

Existe um princípio utilizado pela supervisão:

> "Use dados, não opiniões."

Toda decisão importante deve possuir evidências.

---

# Papel do Supervisor AI

O Supervisor AI deve atuar como uma camada inteligente entre os sistemas operacionais e os gestores.

Suas responsabilidades incluem:

- importar dados;
- consolidar informações;
- aplicar regras de negócio;
- gerar indicadores;
- identificar padrões;
- produzir alertas;
- apoiar decisões.

---

# Fontes de dados

## MK Solutions

Principal sistema operacional.

Utilizado para:

- clientes;
- contratos;
- financeiro;
- tickets;
- suporte;
- mudanças de plano;
- cancelamentos.

É considerado uma das principais fontes de dados.

---

## NPX

Sistema de telefonia.

Responsável por:

- ligações;
- avaliações;
- horários;
- operadores.

---

## MKBot

Sistema de atendimento via WhatsApp.

Responsável por:

- histórico de conversas;
- avaliações CSAT;
- atendimentos por chat.

---

## Colabore

Sistema de ponto.

Responsável por:

- horários;
- atrasos;
- ausências.

---

## Google Sheets

Hoje concentra praticamente todas as consolidações da operação.

Grande parte do trabalho manual ocorre aqui.

---

## Looker Studio

Utilizado para exibição de dashboards.

Os dados são produzidos manualmente antes de serem enviados ao Looker.

---

## AppSheet

Utilizado para registro de horas extras.

---

# Indicadores principais

A operação trabalha principalmente com cinco grupos de indicadores.

## CSAT

Obtido através das avaliações dos clientes.

Fontes:

- NPX
- MKBot

É utilizado para cálculo da RV.

Possui regras de corte e premiações específicas.

---

## Reincidência

Mede retornos técnicos em até 30 dias.

É calculada utilizando regras específicas de abertura e encerramento dos tickets.

Nem todo atendimento técnico entra no cálculo.

Abertura e encerramento precisam atender aos critérios definidos pela operação.

---

## Qualidade

Obtida através do processo de auditoria de qualidade.

Também influencia diretamente a RV.

---

## Cancelamentos

Analisados para identificação de padrões.

Os relatórios são utilizados para tomada de decisões estratégicas.

---

## Upgrades

Representam mudanças de plano.

São acompanhados até:

- alteração realizada;
- primeira mensalidade paga;
- pagamento da premiação.

---

# Renda Variável (RV)

A RV é composta por:

Créditos:

- CSAT
- Reincidência
- Qualidade

Débitos:

- atrasos;
- ausências.

O resultado final determina:

- pagamento;
- saldo zerado;
- geração de Red Flag.

---

# Sistema de Flags

Atualmente existe documentação para o sistema de Flags.

Entretanto, ele ainda não está em funcionamento.

O Supervisor AI deverá considerar inicialmente apenas o cálculo financeiro da RV.

A implementação das Flags ficará para versões futuras.

---

# Extras

O processo atual possui quatro etapas.

- projeção;
- disponibilização;
- validação;
- confirmação.

Após a realização da extra:

- colaborador registra no AppSheet;
- supervisor valida;
- informações seguem para a planilha do RH;
- posteriormente são consolidadas.

---

# Jornada do Supervisor

As principais atividades realizadas atualmente incluem:

- acompanhar indicadores;
- analisar cancelamentos;
- acompanhar upgrades;
- calcular RV;
- validar extras;
- gerar dashboards;
- identificar padrões;
- criar treinamentos;
- apoiar outros setores.

Grande parte dessas tarefas depende de planilhas.

---

# Objetivo do MVP

Eliminar a maior quantidade possível de atividades manuais.

O MVP deverá automatizar:

- importações;
- cálculos;
- indicadores;
- dashboards;
- consolidação dos dados.

---

# Objetivo futuro

Transformar o Supervisor AI em uma plataforma de inteligência operacional.

A arquitetura foi projetada para permitir utilização em outras empresas que possuam processos semelhantes.

A lógica da plataforma deve permanecer genérica.

As regras específicas de cada empresa devem ser implementadas como regras de negócio configuráveis.

---

# Decisões importantes

Durante o levantamento de requisitos foram tomadas algumas decisões arquiteturais.

## O Supervisor AI não será dividido por módulos de negócio.

Recursos como:

- CSAT
- RV
- Extras
- Cancelamentos
- Upgrades

são tratados como regras de negócio.

---

## O sistema será organizado por motores.

- Motor de Importação
- Motor de Processamento
- Motor de Regras

Essa arquitetura reduz duplicação e facilita expansão.

---

## O banco interno não é fonte oficial.

As fontes oficiais permanecem sendo os sistemas externos.

O banco interno existe para consolidação e processamento.

---

# Estado atual do projeto

Concluído:

- levantamento de requisitos;
- documentação da arquitetura;
- documentação das integrações;
- documentação das regras de negócio;
- modelagem inicial do banco;
- definição do MVP;
- definição da arquitetura lógica.

Próxima fase:

Desenvolvimento do MVP.
