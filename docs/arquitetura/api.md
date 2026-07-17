# Arquitetura de API do Supervisor AI

## 1. Objetivo

A API do Supervisor AI será responsável pela comunicação entre os diferentes componentes do sistema.

Ela permitirá que:

- O frontend consulte informações;
- O backend disponibilize dados processados;
- Integrações externas enviem informações;
- Serviços internos troquem informações.

A API funcionará como uma camada intermediária entre dados, regras de negócio e usuários.

---

# 2. Visão geral da comunicação

Fluxo principal:

```
Usuário

↓

Frontend Supervisor AI

↓

API

↓

Backend

↓

Banco de dados
```

Integrações externas:

```
Sistemas externos

↓

Serviços de integração

↓

API

↓

Banco de dados
```

---

# 3. Princípios da API

## Separação de responsabilidades

A API não deve conter regras complexas de negócio.

Exemplo:

A API recebe:

```
Solicitação:
"Qual o valor de RV do colaborador João?"
```

O processamento ocorre:

```
API

↓

Backend

↓

Banco

↓

Resposta organizada
```

---

## Padronização

As respostas devem seguir um padrão para facilitar:

- Frontend;
- Integrações;
- Manutenção.

---

## Segurança

Toda comunicação deve considerar:

- Autenticação;
- Controle de permissões;
- Proteção de dados sensíveis.

---

# 4. Principais grupos de recursos

## Usuários

Responsável pelo controle de acesso.

Possíveis operações:

- Consultar usuário;
- Validar permissão;
- Gerenciar perfil.

---

## Colaboradores

Responsável pelas informações dos operadores.

Possíveis consultas:

- Dados do colaborador;
- Indicadores;
- Desempenho;
- Pagamentos.

---

## Clientes

Responsável pelos dados dos clientes.

Possíveis consultas:

- Cadastro;
- Contrato;
- Histórico;
- Situação financeira.

---

## Atendimentos

Responsável pelas informações de contato.

Possíveis consultas:

- Quantidade de atendimentos;
- Histórico;
- CSAT;
- Classificações.

---

## Indicadores

Responsável pelos dados analíticos.

Exemplos:

- CSAT;
- Reincidência;
- Qualidade;
- Cancelamentos.

---

## Pagamentos

Responsável pelos valores destinados aos colaboradores.

Exemplos:

- Upgrade;
- RV;
- Extras.

---

## Alertas

Responsável pelas notificações geradas pelo sistema.

Exemplos:

- Operador abaixo da média;
- Queda de desempenho;
- Mudança de tendência.

---

# 5. Comunicação com integrações externas

A API deverá permitir que dados sejam recebidos dos sistemas utilizados pela empresa.

Exemplos:

## MK Solutions

Receber:

- Clientes;
- Contratos;
- Tickets;
- Financeiro.

---

## NPX

Receber:

- Ligações;
- Avaliações;
- Dados operacionais.

---

## MKBot

Receber:

- Conversas;
- Atendimento;
- CSAT.

---

## Colabore

Receber:

- Batidas de ponto;
- Ausências.

---

## AppSheet

Receber:

- Registros de extras.

---

# 6. Processos automáticos

A API deve suportar rotinas automáticas.

Exemplo:

```
14:00

Serviço executa coleta

↓

API recebe dados

↓

Backend processa

↓

Banco atualizado
```

---

# 7. Exemplos de consultas futuras

## Situação diária da operação

Solicitação:

"Como está minha equipe hoje?"

Resposta:

- Quantidade de atendimentos;
- CSAT atual;
- Alertas;
- Operadores críticos.

---

## Análise de colaborador

Solicitação:

"Como está o desempenho do operador João?"

Resposta:

- Histórico;
- Indicadores;
- Pontos positivos;
- Pontos de atenção.

---

## Pagamentos

Solicitação:

"Quanto cada colaborador receberá?"

Resposta:

- Upgrade;
- RV;
- Extras;
- Total.

---

# 8. Integração com Inteligência Artificial

A API será responsável por fornecer informações estruturadas para a IA.

A IA não deverá buscar informações diretamente nas fontes originais.

Fluxo:

```
Dados externos

↓

Processamento

↓

API

↓

IA

↓

Resposta ao usuário
```

---

# 9. Controle de permissões

Os acessos deverão respeitar os níveis da empresa.

Exemplo:

## Supervisor

Pode:

- Consultar sua equipe;
- Analisar indicadores;
- Gerar relatórios.

---

## Gerente

Pode:

- Consultar múltiplas equipes;
- Comparar operações;
- Acompanhar resultados gerais.

---

## Administrador

Pode:

- Configurar sistema;
- Gerenciar usuários;
- Alterar parâmetros.

---

# 10. Evolução futura

A API poderá evoluir para:

- Integrações em tempo real;
- Aplicativos móveis;
- Integrações externas;
- Automações avançadas.

---

# 11. Observação

Este documento define a arquitetura de comunicação do Supervisor AI.

A stack técnica do backend está definida em `docs/adr/ADR-003.md`. Endpoints, autenticação e protocolos específicos serão detalhados incrementalmente durante a implementação.
