# Supervisor AI

> Plataforma de Inteligência Operacional para Supervisão de Atendimento.

---

# Visão Geral

O Supervisor AI é uma plataforma desenvolvida para automatizar processos operacionais realizados por supervisores e gestores.

Seu objetivo é centralizar informações provenientes de diversos sistemas da empresa, aplicar regras de negócio automaticamente e transformar dados operacionais em informações úteis para tomada de decisão.

O sistema não substitui os softwares utilizados pela empresa.

Ele atua como uma camada de inteligência entre esses sistemas e seus usuários.

---

# Objetivos

O projeto busca:

- reduzir tarefas manuais;
- eliminar retrabalho;
- centralizar informações;
- automatizar indicadores;
- gerar alertas inteligentes;
- apoiar decisões utilizando dados;
- disponibilizar dashboards em tempo real;
- servir como base para análises realizadas por Inteligência Artificial.

---

# Problema

Hoje a operação depende de diversos sistemas independentes.

Exemplos:

- MK Solutions
- NPX
- MKBot
- Colabore
- Google Sheets
- Looker Studio
- AppSheet

Grande parte das atividades do supervisor consiste em:

- exportar planilhas;
- importar dados;
- aplicar filtros;
- consolidar informações;
- executar cálculos;
- atualizar dashboards;
- conferir pagamentos.

O Supervisor AI elimina grande parte desse trabalho.

---

# Arquitetura

A plataforma segue uma arquitetura baseada em motores.

```
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
```

Essa arquitetura reduz acoplamento, facilita manutenção e permite expansão da plataforma.

Mais detalhes:

- docs/arquitetura/

---

# Motores

## Motor de Importação

Responsável por sincronizar dados provenientes dos sistemas externos.

---

## Motor de Processamento

Responsável por normalizar e relacionar os dados importados.

---

## Motor de Regras

Responsável pela aplicação de toda a lógica operacional.

Exemplos:

- CSAT
- RV
- Reincidência
- Upgrades
- Extras
- Cancelamentos

---

# Fontes de Dados

Atualmente o projeto prevê integração com:

- MK Solutions
- NPX
- MKBot
- Colabore
- AppSheet
- Google Sheets

Novas integrações poderão ser adicionadas por meio de novos conectores.

---

# MVP

A primeira versão possui foco na automação das atividades mais repetitivas.

Principais objetivos:

- importar dados automaticamente;
- calcular indicadores;
- atualizar dashboards;
- eliminar consolidações manuais;
- automatizar pagamentos de RV;
- automatizar pagamentos de Upgrades;
- automatizar validações de Extras;
- gerar alertas operacionais.

---

# Funcionalidades previstas

## Indicadores

- CSAT
- Qualidade
- Reincidência
- Cancelamentos
- Upgrades

---

## Pagamentos

- RV
- Upgrades
- Extras

---

## Dashboards

- Operação
- Indicadores
- Pagamentos
- Alertas

---

## Inteligência Artificial

- Pesquisa em linguagem natural;
- Explicação de indicadores;
- Identificação de padrões;
- Geração de insights;
- Apoio à tomada de decisão.

---

# Estrutura do Projeto

```
SupervisorAI/

backend/
frontend/
database/
docs/
scripts/
tests/

README.md
AGENTS.md
PROJECT_CONTEXT.md
```

---

# Stack Técnica do Backend

O backend será desenvolvido como um monólito modular utilizando:

- Python 3.12;
- FastAPI;
- PostgreSQL;
- SQLAlchemy 2.x e psycopg 3;
- Alembic;
- pytest e Ruff;
- uv para dependências e ambiente.

No desenvolvimento local, o Docker Compose executará somente o PostgreSQL. As operações de banco serão síncronas inicialmente.

Enquanto não houver contrato técnico confirmado para o MK Solutions, o fluxo de importação será validado por uma fonte simulada genérica baseada em arquivos CSV e JSON.

A decisão completa está registrada em `docs/adr/ADR-003.md`.

---

# Documentação

A documentação está organizada em:

```
docs/

arquitetura/
prd/
regras_negocio/
fontes_de_dados/
backlog/
pesquisas/
adr/
```

---

# Arquivos importantes

## README.md

Apresentação geral do projeto.

---

## AGENTS.md

Guia para agentes de Inteligência Artificial.

Define padrões de desenvolvimento e arquitetura.

---

## PROJECT_CONTEXT.md

Contexto operacional da empresa.

Descreve regras de negócio, processos e funcionamento da operação.

---

# Princípios

O projeto segue alguns princípios fundamentais.

- simplicidade;
- reutilização;
- baixo acoplamento;
- alta coesão;
- arquitetura baseada em motores;
- documentação como fonte oficial;
- decisões orientadas por dados.

---

# Estado atual

Atualmente o projeto encontra-se na fase de desenvolvimento do MVP.

As etapas de levantamento de requisitos e arquitetura foram concluídas.

O foco agora é transformar a documentação em software.

---

# Roadmap

## MVP

- Integrações
- Banco
- Backend
- Dashboard
- Indicadores

---

## Versão 2

- IA avançada
- Sistema de Flags
- Configurações
- Treinamentos
- Metas
- Permissões avançadas

---

## Futuro

Transformar o Supervisor AI em uma plataforma reutilizável para diferentes empresas, mantendo uma arquitetura genérica e permitindo a configuração das regras de negócio conforme a operação de cada organização.

---

# Filosofia

O Supervisor AI não é apenas um sistema.

Ele é uma plataforma de inteligência operacional.

Sua missão é transformar grandes volumes de dados operacionais em decisões rápidas, confiáveis e baseadas em evidências.

> Use dados, não opiniões.
