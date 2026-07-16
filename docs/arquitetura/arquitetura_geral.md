# Arquitetura Geral do Supervisor AI

## 1. Visão geral

O Supervisor AI é uma camada de inteligência operacional criada para conectar os sistemas utilizados pela empresa, organizar informações descentralizadas e auxiliar gestores na tomada de decisões.

Atualmente, grande parte das análises operacionais depende de processos manuais envolvendo:

- Exportação de dados;
- Atualização de planilhas;
- Cruzamento de informações;
- Cálculos manuais;
- Construção de dashboards.

O Supervisor AI tem como objetivo centralizar esses processos, transformando dados operacionais em informações rápidas, confiáveis e acionáveis.

---

# 2. Objetivo principal

A primeira versão do Supervisor AI estará concluída quando conseguir automatizar a atualização dos dados utilizados para acompanhamento e pagamento dos colaboradores.

Inicialmente:

- Extras;
- Upgrades;
- CSAT;
- Reincidência;
- Qualidade;
- Atrasos;
- Faltas.

O sistema deverá coletar, processar e apresentar essas informações de forma mais rápida e confiável.

---

# 3. Arquitetura em camadas

A arquitetura do Supervisor AI será dividida em camadas:

```
Usuário

↓

Frontend

↓

API

↓

Backend

↓

Banco de dados

↓

Integrações externas
```

Cada camada possui uma responsabilidade específica.

---

# 4. Integrações externas

São os sistemas onde os dados nascem.

Principais fontes:

## MK Solutions

Responsável por:

- Clientes;
- Contratos;
- Financeiro;
- Tickets;
- Informações operacionais.

---

## MKBot

Responsável por:

- Atendimentos via WhatsApp;
- Histórico de conversas;
- Avaliações de satisfação.

---

## NPX

Responsável por:

- Ligações;
- Notas de satisfação;
- Registro de ponto relacionado ao atendimento.

---

## Colabore

Responsável por:

- Batidas de ponto;
- Controle de jornada;
- Ausências.

---

## AppSheet

Responsável atualmente pelo registro de:

- Horas extras;
- Informações enviadas ao RH.

---

# 5. Camada de armazenamento

O banco de dados próprio do Supervisor AI será responsável por armazenar informações organizadas.

Ele deverá manter:

- Dados originais;
- Dados tratados;
- Histórico;
- Resultados calculados.

O objetivo é evitar dependência direta das planilhas atuais.

---

# 6. Camada Backend

O backend será responsável pela inteligência operacional do sistema.

Responsabilidades:

## Coleta

Buscar informações nos sistemas externos.

---

## Processamento

Transformar dados brutos em informações úteis.

Exemplo:

```
Atendimento bruto

↓

Identificação do colaborador

↓

Cálculo de CSAT

↓

Indicador atualizado
```

---

## Regras de negócio

Aplicar as regras existentes na empresa.

Exemplos:

- Cálculo de upgrade;
- Cálculo de RV;
- Validação de extras;
- Identificação de reincidência.

---

## Inteligência

Gerar:

- Alertas;
- Análises;
- Resumos;
- Recomendações.

---

# 7. API

A API será responsável pela comunicação entre as partes do sistema.

Ela permitirá:

- Frontend consultar informações;
- Sistemas enviarem dados;
- Serviços internos trocarem informações.

A API será uma camada intermediária, evitando que usuários ou aplicações acessem diretamente o banco.

---

# 8. Frontend

O frontend será a interface utilizada pelos gestores.

Objetivo:

Permitir que um supervisor consiga compreender a operação rapidamente.

A primeira experiência esperada:

Ao iniciar o expediente:

```
Supervisor abre o sistema

↓

Visualiza alertas

↓

Analisa indicadores

↓

Identifica problemas

↓

Toma decisões
```

---

# 9. Fluxo de dados

Exemplo de atendimento:

```
Cliente realiza contato

↓

Atendimento registrado no NPX/MKBot

↓

Dados coletados pelo Supervisor AI

↓

Banco atualizado

↓

Indicadores processados

↓

Dashboard atualizado

↓

Gestor analisa resultado
```

---

# 10. Fluxo financeiro dos colaboradores

Exemplo de upgrade:

```
Cliente realiza mudança de plano

↓

Ticket criado no MK

↓

Mudança identificada pelo Supervisor AI

↓

Sistema verifica pagamento

↓

Calcula premiação

↓

Valor enviado para acompanhamento
```

---

Exemplo de RV:

```
Indicadores coletados

↓

CSAT/Reincidência/Qualidade

↓

Cálculo de créditos

↓

Atrasos/Faltas

↓

Cálculo de débitos

↓

Resultado final
```

---

# 11. Princípios do sistema

## Dados antes de opiniões

Todas as decisões devem ser baseadas em evidências.

---

## Histórico

O sistema deve permitir análises futuras.

Exemplo:

"Como o desempenho dessa equipe mudou nos últimos meses?"

---

## Automação

Eliminar tarefas repetitivas e manuais.

---

## Simplicidade

A ferramenta deve facilitar a rotina dos gestores, não aumentar sua complexidade.

---

# 12. Visão de longo prazo

O Supervisor AI deve evoluir de uma plataforma de acompanhamento para um assistente operacional completo.

Possíveis evoluções:

- Identificação automática de problemas;
- Sugestão de ações;
- Criação automática de relatórios;
- Análises preditivas;
- Auxílio na tomada de decisão.

---

# 13. Estado atual da arquitetura

Documentos relacionados:

```
arquitetura/
├── api.md
├── arquitetura_geral.md
├── backend.md
├── banco.md
├── entidades.md
├── frontend.md
├── integracoes.md
└── visao_geral.md
```

Esta documentação representa a arquitetura inicial do Supervisor AI e será atualizada conforme novas decisões técnicas forem tomadas.
