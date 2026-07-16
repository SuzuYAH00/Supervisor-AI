# Arquitetura Lógica

## Objetivo

Este documento descreve a arquitetura lógica do Supervisor AI.

Seu objetivo é definir como o sistema processa informações, independentemente da tecnologia utilizada.

Enquanto outros documentos descrevem módulos, banco de dados ou integrações, este documento explica o fluxo lógico que conecta todos esses elementos.

---

# Princípios

O Supervisor AI não é composto por diversos módulos independentes.

Ele é uma plataforma de inteligência operacional construída sobre um fluxo único de processamento de dados.

Os módulos visíveis ao usuário (CSAT, Upgrades, RV, Extras, Cancelamentos, etc.) representam apenas regras de negócio aplicadas sobre uma base única de informações.

---

# Visão Geral

```
Fontes Externas

↓

Conectores

↓

Motor de Importação

↓

Banco de Dados

↓

Motor de Processamento

↓

Motor de Regras de Negócio

↓

Banco Consolidado

↓

Dashboard

↓

Inteligência Artificial
```

Todo dado percorre obrigatoriamente esse fluxo.

---

# Fontes Externas

São os sistemas oficiais utilizados pela empresa.

Exemplos:

- MK Solutions
- NPX
- MKBot
- Colabore
- AppSheet
- Google Sheets
- Outras integrações futuras

O Supervisor AI não altera essas bases.

Seu papel é apenas consumir informações.

---

# Conectores

Cada sistema externo possui um único conector responsável por traduzir seus dados para o formato interno do Supervisor AI.

Exemplo:

```
MK

↓

Conector MK

↓

Motor de Importação
```

Outro exemplo:

```
NPX

↓

Conector NPX

↓

Motor de Importação
```

Cada conector conhece apenas o sistema ao qual pertence.

Ele não possui regras de negócio.

Sua responsabilidade é apenas importar dados.

---

# Motor de Importação

O Motor de Importação é responsável por:

- Executar importações;
- Detectar novos registros;
- Atualizar registros existentes;
- Registrar logs de sincronização;
- Encaminhar dados para processamento.

Esse componente é único para toda a plataforma.

Novos sistemas integrados reutilizam o mesmo motor.

---

# Banco de Dados

Após a importação, os dados são armazenados em um modelo interno padronizado.

Esse banco representa a base operacional do Supervisor AI.

Ele é desacoplado da estrutura dos sistemas externos.

---

# Motor de Processamento

Após armazenados, os dados passam pelo Motor de Processamento.

Responsabilidades:

- Normalizar informações;
- Relacionar entidades;
- Consolidar dados;
- Preparar informações para aplicação das regras de negócio.

Esse motor não interpreta regras específicas da empresa.

Seu papel é apenas organizar os dados.

---

# Motor de Regras de Negócio

Esse é o núcleo funcional da plataforma.

É aqui que toda a inteligência operacional é aplicada.

Exemplos:

- Cálculo de CSAT;
- Cálculo de RV;
- Identificação de reincidências;
- Validação de extras;
- Identificação de upgrades;
- Consolidação de pagamentos;
- Detecção de padrões;
- Geração de alertas.

Cada regra atua sobre a mesma base consolidada de informações.

---

# Banco Consolidado

Após o processamento das regras, os resultados ficam disponíveis em uma base consolidada.

Essa base é otimizada para consultas rápidas.

Ela alimenta:

- Dashboards;
- Relatórios;
- Inteligência Artificial.

---

# Dashboard

A interface do Supervisor AI consulta apenas o banco consolidado.

Isso garante:

- Alta velocidade;
- Baixo tempo de resposta;
- Independência das integrações externas.

O Dashboard nunca consulta diretamente os sistemas externos.

---

# Inteligência Artificial

A IA também utiliza exclusivamente o banco consolidado.

Isso garante que:

- As respostas sejam consistentes;
- Os dados possuam rastreabilidade;
- As análises utilizem a mesma base apresentada ao usuário.

A IA não deverá consultar diretamente os sistemas externos.

---

# Organização da Plataforma

A arquitetura NÃO será organizada por módulos de negócio.

Evitar estruturas como:

```
/upgrade

/csat

/reincidencia

/extras

/cancelamentos
```

Essa abordagem aumenta o acoplamento entre componentes.

---

A organização deverá ser baseada nos motores da plataforma.

```
Conectores

↓

Motor de Importação

↓

Motor de Processamento

↓

Motor de Regras

↓

Banco Consolidado

↓

Dashboard

↓

IA
```

Novas funcionalidades deverão ser implementadas, sempre que possível, como novas regras de negócio dentro do Motor de Regras, reutilizando toda a infraestrutura existente.

---

# Benefícios

Essa arquitetura proporciona:

- Baixo acoplamento;
- Reutilização de código;
- Escalabilidade;
- Facilidade para novas integrações;
- Facilidade para novos indicadores;
- Maior manutenibilidade;
- Menor duplicação de lógica.

---

# Evolução da Plataforma

A arquitetura foi projetada para permitir que o Supervisor AI evolua continuamente.

Adicionar novos sistemas externos exigirá apenas:

1. Criar um novo conector;
2. Configurar o Motor de Importação;
3. Adicionar novas regras de negócio, quando necessário.

Toda a infraestrutura restante permanecerá inalterada.

---

# Decisão Arquitetural

Esta arquitetura estabelece que:

- O Supervisor AI é uma plataforma de processamento de dados operacionais.
- Os módulos visíveis ao usuário representam regras de negócio e não divisões técnicas do sistema.
- Todo processamento deverá reutilizar os motores centrais da plataforma.
- A expansão futura deverá ocorrer por meio da criação de novos conectores e novas regras de negócio, evitando duplicação de código e dependências desnecessárias.
