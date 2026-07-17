# Regra de Negócio — Upgrade

> Especificação funcional consolidada: [Upgrades e remuneração](upgrades_e_remuneracao.md).

## Objetivo

Definir as regras utilizadas pelo Supervisor AI para identificar, validar, calcular e acompanhar premiações provenientes de Upgrades realizados pelos colaboradores.

Este documento descreve apenas as regras de negócio.

Informações comerciais como planos, produtos e valores deverão ser obtidas diretamente do MK Solutions.

---

# Fonte dos Dados

O Supervisor AI deverá consultar diretamente o MK Solutions para obter informações referentes a:

- Clientes
- Contratos
- Planos
- Produtos
- Alterações de Plano
- Pagamentos
- Histórico de Upgrades

O Supervisor AI não deverá manter listas fixas de planos ou produtos.

---

# Conceitos

Para o Supervisor AI, um Upgrade representa qualquer alteração contratual realizada pelo colaborador que gere direito à premiação.

Existem dois tipos de Upgrade:

- Upgrade com renovação de fidelidade.
- Venda de adicionais.

Embora operacionalmente ambos sejam chamados de Upgrade, possuem regras diferentes para cálculo da premiação.

---

# Classificação dos Produtos

O comportamento do produto é mais importante do que sua classificação comercial.

Cada produto deverá possuir uma regra de premiação associada.

Exemplos de comportamentos:

| Comportamento | Regra |
|---------------|-------|
| Renova fidelidade | Premiação pelo valor integral do novo plano |
| Não renova fidelidade | Premiação pelo valor do adicional vendido |
| Cancelamento antes de 90 dias | Desconto em dobro da premiação |
| Mesh | Comercialmente é adicional, mas comporta-se como renovação de fidelidade |

---

# Regras de Negócio

## Upgrade com Renovação de Fidelidade

Sempre que houver alteração contratual que gere renovação da fidelidade do cliente, o colaborador receberá como premiação o valor integral do novo plano contratado.

O valor efetivamente pago pelo cliente não altera o cálculo da premiação.

Basta existir confirmação do primeiro pagamento para que a premiação seja liberada.

---

## Venda de Adicionais

Produtos que não geram renovação de fidelidade concedem premiação equivalente ao valor do adicional vendido.

Esses adicionais deverão permanecer em acompanhamento durante 90 dias.

Caso sejam cancelados antes desse período, será aplicado desconto equivalente ao dobro do valor originalmente pago.

---

## Mesh

Apesar de ser classificado comercialmente como adicional, o Mesh deverá ser tratado como produto que gera renovação de fidelidade.

Sua premiação seguirá exatamente as mesmas regras utilizadas para upgrades de plano.

---

# Liberação da Premiação

Após a venda, o Upgrade permanecerá no estado:

"Aguardando Primeiro Pagamento"

A premiação somente será liberada após confirmação do primeiro pagamento do novo contrato.

A confirmação independe do valor pago.

São considerados válidos:

- pagamento integral;
- pagamento proporcional;
- pagamento negociado.

---

# Cancelamentos

## Antes do primeiro pagamento

Caso o cliente cancele antes da confirmação do primeiro pagamento, nenhuma premiação será liberada.

---

## Após a liberação

Uma vez liberada, a premiação não poderá ser removida em razão de cancelamento do contrato.

Essa regra existe porque a renovação da fidelidade gera multa contratual suficiente para compensar o custo da premiação.

---

# Múltiplos Upgrades

Não existe limite para quantidade de premiações geradas para um mesmo cliente.

Cada alteração contratual deverá ser analisada individualmente.

Sempre que cumprir as regras estabelecidas, uma nova premiação poderá ser concedida.

---

# Fluxo

Alteração contratual realizada

↓

Supervisor AI registra o Upgrade

↓

Premiação fica aguardando confirmação do pagamento

↓

Supervisor AI identifica o primeiro pagamento

↓

Premiação é liberada

↓

Premiação enviada para cálculo mensal

↓

Pagamento ao colaborador

---

# Dados Necessários

Para cada Upgrade, o Supervisor AI deverá registrar:

- Cliente
- Operador responsável
- Data da alteração contratual
- Tipo da alteração
- Produto(s) envolvidos
- Valor da premiação
- Situação da premiação
- Data do primeiro pagamento
- Situação do acompanhamento
- Histórico de alterações

---

# Observações

Este documento define exclusivamente as regras de negócio relacionadas ao processo de Upgrade.

Planos, produtos, valores e demais informações comerciais deverão ser obtidos diretamente do MK Solutions, respeitando a decisão arquitetural definida na ADR-002.
