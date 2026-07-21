# Registro técnico — Rules Engine Fase C

## Escopo corrigido

A Fase C representa exclusivamente contexto operacional e autoria. Ela decide
se as informações operacionais são suficientes e elegíveis para fases
posteriores, sem decidir mérito comercial ou remuneração.

## Referências relidas

- `docs/arquitetura/rules_engine.md`
- `docs/arquitetura/modelo_de_dominio_upgrades.md`
- `docs/regras_negocio/upgrades_e_remuneracao.md`
- `backend/src/supervisor_ai/rules_engine/operational_context.py`
- `backend/src/supervisor_ai/rules_engine/conclusion_names.py`
- `backend/tests/rules_engine/test_operational_context.py`

## Decisões arquiteturais

1. Todas as regras da Fase C consomem exclusivamente
   `available_conclusions`. O `EvaluationContext` é recebido apenas pelo
   contrato `Rule` e não é lido.
2. `OperationalContextEligibilityRule` substitui
   `OperationalRemunerationFlowRule`. Sua saída descreve apenas elegibilidade
   do contexto operacional.
3. A regra final depende somente de ticket presente, abertura pelo Suporte,
   autor do ticket identificado e ausência de autoria duplicada.
4. Nenhuma conclusão de `CommercialClassificationName` é importada ou consumida
   pela Fase C. Upgrade, downgrade, receita e adicionais não influenciam a
   elegibilidade operacional.
5. A autoria comercial é derivada exclusivamente de
   `TICKET_AUTHOR_IDENTIFIED` ou `TICKET_AUTHOR_MISSING`. O conceito genérico
   `AUTHOR_CANDIDATE` foi removido.
6. A identidade do executor permanece representável pelos fatos
   `EXECUTOR_IDENTIFIED`, `EXECUTOR_MISSING`, `EXECUTOR_NOT_EVALUABLE` e
   `EXECUTOR_INCONSISTENT`. Esses fatos são auditáveis, mas não substituem o
   autor do ticket nem participam da elegibilidade operacional.
7. Ticket ausente, ticket fora do Suporte ou autor ausente tornam o contexto
   operacional inelegível.
8. Autoria duplicada torna o contexto não avaliável e gera
   `manual_review_required`; nenhuma regra escolhe automaticamente um autor.
9. Inconsistência tem precedência. Entradas necessárias ausentes ou não
   avaliáveis permanecem `NOT_EVALUABLE`.
10. O resolvedor comum em `_conclusion_resolution.py` detecta nomes duplicados,
    não depende da ordem de entrada e mantém IDs de suporte determinísticos.
11. Todas as saídas são `DOMAIN_DECISION` com `TRUE`, `NOT_EVALUABLE` ou
    `INCONSISTENT`; não há proposições `FALSE`.

## Regras da Fase C

- `TicketPresenceRule`
- `TicketSupportRule`
- `CommercialAuthorRule`
- `DuplicateAuthorRule`
- `ManualReviewRule`
- `OperationalContextEligibilityRule`

Todas pertencem a `RulePhase.AUTHORSHIP_AND_ELIGIBILITY` e satisfazem
estruturalmente `Rule`.

## Decisões produzidas

- `ticket_present` / `ticket_missing`;
- `support_ticket` / `non_support_ticket`;
- `commercial_author_identified` / `commercial_author_missing`;
- `duplicate_author` / `no_duplicate_author`;
- `manual_review_required`;
- `operational_context_eligible` / `operational_context_ineligible`;
- estados específicos `*_not_evaluable` e `*_inconsistent`.

## Cobertura de testes

- contexto operacional elegível;
- ticket ausente;
- ticket fora do Suporte;
- autor do ticket ausente;
- autoria duplicada e revisão manual;
- executor diferente do autor sem alterar elegibilidade ou autoria;
- executor ausente sem alterar elegibilidade;
- entrada necessária não avaliável;
- entrada inconsistente;
- nomes duplicados;
- ordem independente, determinismo e ausência de mutação;
- ausência de dependência de `CommercialClassificationName`;
- ausência de `CandidateDomainEvent`.

## Arquivos criados na entrega

- `backend/src/supervisor_ai/rules_engine/_conclusion_resolution.py`
- `backend/src/supervisor_ai/rules_engine/operational_context.py`
- `backend/tests/rules_engine/test_operational_context.py`
- `docs/codex_logs/fase-c.md`

## Arquivos alterados na entrega

- `backend/src/supervisor_ai/rules_engine/__init__.py`
- `backend/src/supervisor_ai/rules_engine/commercial_classification.py`
- `backend/src/supervisor_ai/rules_engine/conclusion_names.py`
- `backend/tests/rules_engine/test_rules_engine_contracts.py`

`commercial_classification.py` foi alterado apenas para reutilizar o resolvedor
comum, sem mudança semântica na Fase B.

## Validações executadas

```text
env UV_CACHE_DIR=/tmp/supervisor-ai-uv-cache \
  uv --project backend run ruff check \
  backend/src/supervisor_ai/rules_engine \
  backend/tests/rules_engine

env UV_CACHE_DIR=/tmp/supervisor-ai-uv-cache \
  uv --project backend run pytest backend/tests/rules_engine

env UV_CACHE_DIR=/tmp/supervisor-ai-uv-cache \
  uv --project backend run pytest backend/tests

git diff --check
git status --short
```

Resultados:

- Ruff: `All checks passed!`;
- testes do Rules Engine: `111 passed in 0.12s`;
- suíte completa: `175 passed in 0.47s`;
- `git diff --check`: sem erros;
- busca estática na implementação da Fase C: nenhuma dependência de
  `CommercialClassificationName` ou de suas conclusões;
- nenhum commit realizado.

## Limites preservados

- nenhum acesso a evidência bruta, banco, API ou sistema externo;
- nenhuma dependência das classificações comerciais da Fase B;
- nenhum cálculo de remuneração, pagamento, comissão ou crédito;
- nenhuma carteira ou persistência;
- nenhum `CandidateDomainEvent`;
- nenhum commit.
