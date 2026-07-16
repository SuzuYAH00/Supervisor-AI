# Arquitetura Backend do Supervisor AI

## 1. Objetivo

O backend do Supervisor AI será responsável por controlar toda a lógica de funcionamento da plataforma.

Ele será a camada responsável por:

- Coletar informações dos sistemas externos;
- Processar dados;
- Aplicar regras de negócio;
- Armazenar informações;
- Gerar análises;
- Disponibilizar informações para a interface do usuário.

O backend será o núcleo operacional do Supervisor AI.

---

# 2. Responsabilidades principais

## Coleta de dados

Responsável por buscar informações dos sistemas externos.

Exemplos:

- Atendimentos do NPX;
- Atendimentos do MKBot;
- Tickets do MK Workspace;
- Pagamentos do MK Financeiro;
- Dados de ponto;
- Dados de extras.

---

## Processamento de dados

Responsável por transformar dados brutos em informações úteis.

Exemplo:

Entrada:

```
Atendimento encerrado
Nota do cliente: 10
Operador: João
```

Processamento:

```
Identificar operador

Atualizar CSAT

Calcular média

Comparar com equipe

Gerar indicador
```

---

## Regras de negócio

Responsável por aplicar as regras definidas pela empresa.

Exemplos:

- Cálculo de Upgrade;
- Cálculo de RV;
- Cálculo de Extras;
- Identificação de reincidência;
- Critérios de cancelamento.

---

## Geração de inteligência

Responsável por utilizar os dados processados para gerar informações úteis.

Exemplos:

- Alertas;
- Resumos diários;
- Identificação de padrões;
- Sugestões de ação.

---

# 3. Fluxo geral do backend

O funcionamento esperado:

```
Sistemas externos

↓

Coletores

↓

Banco de dados

↓

Processadores

↓

Regras de negócio

↓

Camada de inteligência

↓

Interface Supervisor AI
```

---

# 4. Módulos internos do backend

## Módulo de integração

Responsável pela comunicação com sistemas externos.

Exemplos:

- MK Solutions;
- NPX;
- MKBot;
- Colabore;
- AppSheet.

Responsabilidades:

- Autenticação;
- Consulta;
- Recebimento de dados;
- Tratamento inicial.

---

# Módulo de sincronização

Responsável por controlar quando os dados serão atualizados.

Exemplos:

Atualização de indicadores:

```
14:00

17:00

22:00
```

Responsabilidades:

- Executar rotinas automáticas;
- Controlar histórico;
- Evitar duplicação.

---

# Módulo de processamento

Responsável por transformar dados coletados.

Exemplos:

Atendimentos:

```
Dados do MKBot

↓

Separação por operador

↓

Cálculo CSAT

↓

Indicador atualizado
```

---

# Módulo de regras de negócio

Centraliza as regras operacionais.

Exemplos:

## Upgrade

Avaliar:

- Mudança de plano;
- Valor novo;
- Pagamento;
- Elegibilidade.

---

## RV

Avaliar:

- CSAT;
- Reincidência;
- Qualidade;
- Atrasos;
- Faltas.

---

## Extras

Avaliar:

- Horários;
- Intervalo;
- Tipo de extra;
- Conflitos de jornada.

---

# Módulo financeiro

Responsável pela consolidação dos valores pagos.

Exemplos:

```
Upgrade

+

RV

+

Extras

=

Pagamento total
```

---

# Módulo de alertas

Responsável por identificar situações importantes.

Exemplos:

- Operador abaixo da média;
- Crescimento de cancelamentos;
- Queda de indicador;
- Necessidade de ação.

---

# 5. Processamento automático

O Supervisor AI deve reduzir atividades manuais através de rotinas automáticas.

Exemplo atual:

```
Supervisor exporta MK

↓

Atualiza planilha

↓

Calcula indicadores

↓

Atualiza dashboard
```

Fluxo futuro:

```
Supervisor AI consulta MK

↓

Processa dados

↓

Atualiza indicadores

↓

Exibe informações
```

---

# 6. Controle de duplicidade

Como alguns sistemas trabalham com exportações periódicas, o backend deverá controlar registros duplicados.

Exemplo atual:

Exportação 14h:

```
Todos atendimentos até 14h
```

Exportação 17h:

```
Todos atendimentos até 17h

-

Atendimentos já coletados
```

O Supervisor AI deverá utilizar identificadores únicos para evitar registros repetidos.

Exemplos:

- Protocolo;
- ID atendimento;
- Código cliente.

---

# 7. Histórico de processamento

Todas as execuções importantes devem ser registradas.

Exemplos:

- Última sincronização;
- Quantidade de dados importados;
- Erros encontrados;
- Alterações realizadas.

---

# 8. Integração com Inteligência Artificial

A IA será uma camada adicional utilizando os dados processados pelo backend.

Ela não deve acessar dados brutos diretamente.

Fluxo:

```
Sistemas

↓

Backend

↓

Dados organizados

↓

IA

↓

Resposta ao gestor
```

---

# 9. Segurança

O backend deverá controlar:

- Permissões;
- Acesso por perfil;
- Dados sensíveis;
- Histórico de alterações.

Exemplo:

Supervisor:

- Visualiza sua operação.

Gerente:

- Visualiza todas equipes.

Administrador:

- Gerencia configurações.

---

# 10. Evolução futura

Possíveis evoluções:

- Integrações em tempo real;
- Automações de processos;
- Previsões utilizando IA;
- Recomendações automáticas;
- Assistente operacional completo.

---

# 11. Observação

Este documento define responsabilidades do backend.

Decisões técnicas específicas como linguagem, framework, infraestrutura e hospedagem serão definidas posteriormente em documentos próprios.
