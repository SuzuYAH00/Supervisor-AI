# Auditoria PostgreSQL do domínio de Upgrade no MK

## Escopo

Este documento registra a descoberta factual realizada em 27 de agosto de 2026
no PostgreSQL real do MK. A investigação foi exclusivamente read-only, começou
por metadata e usou apenas agregados e pequenas amostras sanitizadas.

Não foram executados comandos de escrita, DDL ou procedures. Credenciais, DSN e
dados pessoais não foram registrados.

## Segurança da sessão

- transporte: não-TLS, habilitado somente por `MK_DB_SSLMODE=disable` explícito;
- o default do projeto continua sendo `require`;
- `SELECT 1`: executado com sucesso;
- `transaction_read_only`: `on`;
- `default_transaction_read_only`: `on`.

A aceitação operacional do transporte não-TLS não altera a exigência de sessão
read-only.

## Classificações

| Classificação | Resultado |
|---|---|
| `MK_DB_TRANSPORT` | `NON_TLS_EXPLICIT` |
| `MK_DB_READ_ONLY` | `CONFIRMED` |
| `REAL_MK_CONNECTION` | `PASSED` |
| `CONTRACT_SOURCE` | `FOUND` |
| `CURRENT_PLAN_SOURCE` | `FOUND` |
| `PLAN_CHANGE_HISTORY` | `FOUND` |
| `OLD_PLAN` | `FOUND` |
| `NEW_PLAN` | `FOUND` |
| `PLAN_CHANGED_AT` | `FOUND` |
| `PLAN_CHANGED_BY` | `FOUND` |
| `UPGRADE_ATTENDANCE_IDENTIFICATION` | `FOUND` |
| `ATTENDANCE_PLAN_CHANGE_LINK` | `TEMPORAL_ONLY` |
| `PLAN_CHANGE_OPERATOR` | `DERIVABLE` |
| `PLAN_CHANGE_TIMESTAMP` | `DATETIME` |
| `CONTRACT_VALUE_HISTORY` | `PARTIAL` |
| `UPGRADE_PAYMENT_EVIDENCE` | `PARTIAL` |
| `CAN_DISCOVER_UPGRADE_FROM_DB` | `YES_DETERMINISTIC` |
| `CAN_ENRICH_UPGRADE_FROM_DB` | `PARTIAL` |
| `CAN_VALIDATE_UPGRADE_FINANCIALLY` | `PARTIAL` |
| `UPGRADE_AUTOMATION_COVERAGE` | `PARTIAL` |

## Mapa do schema comercial

O schema não declara FKs para a maior parte dessas relações. Os vínculos abaixo
foram comprovados por colunas, índices, definições de views e agregados; uma
implementação futura deverá tratá-los como contratos externos explicitamente
validados.

| Relação | PK | Descrição | Relacionamentos e campos relevantes |
|---|---|---|---|
| `mk_pessoas` | `codpessoa` | Cliente/pessoa | Referenciada por `mk_contratos.cliente`; contém situação cadastral, mas PII não faz parte da integração proposta. |
| `mk_contratos` | `codcontrato` | Estado atual do contrato | `cliente`, `plano_acesso`, `cancelado`, `suspenso`, `adesao`, `data_hora_ativacao`, `dt_venda`, `dt_ativacao`. |
| `mk_conexoes` | `codconexao` | Conexão técnica | `codcliente`, `contrato`, `codplano_acesso`, `velocidades_formatadas`; o plano técnico não deve substituir o plano comercial do contrato. |
| `mk_planos_acesso` | `codplano` | Catálogo de planos | `descricao`, `vlr_mensalidade`, velocidades, modalidade e atributos técnicos/comerciais. |
| `mk_planos_acesso_composicao_valor` | `codplanocomposicao` | Composição do plano | `plano`, item/produto, tributação e `vlr_proporcional`; útil para adicionais e composição, não representa sozinho o valor contratado. |
| `mk_contratos_historicos` | `codcontratohist` | Histórico vigente de contrato | `cd_contrato`, `dt_hr`, `operador`, `cd_operacao`, `cd_plano_velho`, `cd_plano_novo`, `vlr`, `tx_extra`. |
| `mk_contratos_operacoes` | `codcontratooperacao` | Catálogo de operações | Código `4` = Upgrade e código `5` = Downgrade na amostra auditada. |
| `mk_contratos_upgrades` | `codcontratoupgrade` | Histórico legado explícito | `contrato`, data/hora, operador, planos, `vlr_up_down`, `modificacao`; possui dados somente até janeiro de 2018. |
| `mk_contratos_eventos` | `codevento` | Eventos textuais do contrato | Contrato, timestamp, usuário, descrição e informação adicional. |
| `mk_contratos_alteracao` | `codcontalter` | Alteração textual da conexão/contrato | Contrato, usuário, data/hora e informações textuais. Não substitui a transição estruturada. |
| `mk_atendimento` | `codatendimento` | Atendimento/ticket | Cliente, conexão, contrato, protocolo, processo, subprocesso, classificações, abertura, encerramento e operadores. |
| `fr_usuario` | `usr_codigo` | Identidade do usuário MK | Login e nome; a integração canônica deve usar `external_identity=str(usr_codigo)`. |
| `fr_log_event` | `log_id` | Auditoria genérica | Data/hora, formulário, operação, usuário, chave e conteúdo. Há eventos do formulário “Assistente - Upgrade/Downgrade”. |

Também foram encontradas functions relacionadas a alteração de contrato e
faturamento. Elas foram apenas inventariadas; nenhuma function ou procedure foi
executada.

## Fluxo do contrato e plano atual

```text
mk_pessoas.codpessoa
  -> mk_contratos.cliente
  -> mk_contratos.plano_acesso
  -> mk_planos_acesso.codplano
```

Dos 82.237 contratos observados, todos tinham cliente e plano; 81.769 planos
continuavam presentes no catálogo e 81.493 contratos possuíam data de ativação.
Existiam conexões para 76.392 contratos.

O plano da conexão não deve ser usado isoladamente como plano comercial. Apenas
9.230 contratos tinham alguma conexão cujo plano coincidia com o plano do
contrato. Entre 18.309 contratos com Upgrade/Downgrade histórico, o último plano
novo coincidia com `mk_contratos.plano_acesso` em 14.914 e com alguma conexão em
5.449.

## Fluxo de alteração

```text
mk_contratos.codcontrato
  -> mk_contratos_historicos.cd_contrato
  -> cd_operacao (4 Upgrade / 5 Downgrade)
  -> cd_plano_velho / cd_plano_novo
  -> mk_planos_acesso
  -> operador + dt_hr
```

Foram observadas 27.843 linhas classificadas pelos códigos 4 ou 5, entre janeiro
de 2018 e agosto de 2026: 20.796 Upgrades e 7.047 Downgrades. O timestamp completo
e o operador estavam presentes em todas.

O histórico preserva cadeias com várias mudanças: 6.101 contratos possuíam mais
de uma transição e o máximo observado foi 15. Logo, a origem suporta sequências
`A -> B -> C`, sem reduzir o histórico a plano original versus plano atual.

Há lacunas históricas: 5.339 linhas não tinham plano antigo e 2.226 não tinham
plano novo. Além disso, planos antigos podem ter sido removidos do catálogo.
Essas lacunas não impedem descobrir que a operação ocorreu, mas podem impedir o
enriquecimento completo.

### Operador

`mk_contratos_historicos.operador` conserva o login textual. Parte dos logins
atuais resolve para `fr_usuario.usr_codigo`; logins históricos/removidos não
resolvem integralmente. O identificador canônico é, portanto, derivável quando
o usuário ainda está no catálogo, sem fazer match por nome.

### Valor

`mk_contratos_historicos.vlr` e `mk_contratos_upgrades.vlr_up_down` representam
evidência de variação, mas não oferecem de modo uniforme os valores recorrentes
efetivamente contratados antes e depois. O catálogo traz
`mk_planos_acesso.vlr_mensalidade`, porém preço de tabela não equivale
necessariamente ao valor efetivo após descontos, promoções, Mesh e adicionais.

Por isso, mudança de plano é explícita, enquanto `OLD_VALUE` e `NEW_VALUE` são
apenas deriváveis em parte e exigem uma composição financeira validada.

## Relação com atendimento

Os catálogos identificam explicitamente:

- processos `UPGRADE de Plano` e `DOWNGRADE de Plano`;
- subprocessos `Mudança Plano`, `Upgrade` e `Downgrade`;
- classificações `UPGRADE` e `Upgrade S/ Alterar Valor`.

Foram localizados 21.004 atendimentos compatíveis; 20.913 tinham contrato,
20.931 conexão e todos tinham cliente e protocolo.

Não foi encontrada FK, coluna de atendimento/protocolo ou referência equivalente
em `mk_contratos_historicos` ou `mk_contratos_upgrades`. O payload histórico não
mencionava atendimento ou protocolo. No mesmo dia e contrato, apenas 5.293
eventos tinham exatamente um atendimento candidato, 2.029 tinham vários e
20.521 não tinham nenhum. Portanto:

```text
atendimento -> alteração de plano = TEMPORAL_ONLY
```

Essa proximidade não pode ser promovida a vínculo determinístico nem usada para
atribuir remuneração automaticamente.

## Fluxo financeiro

O vínculo financeiro factual principal é:

```text
mk_contratos.codcontrato
  -> mk_plano_contas.codvinculado
  -> mk_contas_faturadas.cd_conta
  -> mk_faturas.codfatura
  -> liquidação / parcial / estorno
```

Há ainda um vínculo mais específico ao plano faturado:

```text
mk_contratos_historicos.cd_contrato + cd_plano_novo
  -> mk_doc_fiscal_itens.cd_contrato + cd_plano
  -> mk_doc_fiscal.cd_fatura
  -> mk_faturas
```

Campos disponíveis em `mk_faturas` incluem emissão, vencimento, valor, status de
liquidação, timestamp e valor pago, pagamento parcial, exclusão e estorno.
`mk_faturas_historicos` preserva operações, liquidações parciais e estornos.

Nos 500 eventos mais recentes, 259 tinham conta/fatura posterior dentro de 120
dias e 72 já estavam pagas. Nos 200 mais recentes, 37 tinham item fiscal ligado
simultaneamente ao contrato e ao plano novo; 23 dessas faturas estavam pagas.

Os dados permitem provar fatura e pagamento quando o vínculo existe. Eles não
identificam de forma universal e inequívoca a primeira fatura do novo valor,
nem garantem que `valor_total` seja somente a recorrência do plano. Por isso a
validação financeira automática é parcial diante do contrato atual do Rules
Engine.

## Matriz de cobertura do Upgrade atual

| Fato exigido | Fonte atual | Fonte PostgreSQL MK | Disponibilidade | Confiança |
|---|---|---|---|---|
| Cliente e contrato | Evento importado | `mk_contratos` / `mk_pessoas` | Disponível | Explícita |
| Plano anterior e novo | Evidências pré-importadas | `mk_contratos_historicos.cd_plano_velho/cd_plano_novo` | Disponível com nulos históricos | Explícita |
| Velocidade anterior e atual | Evidências pré-importadas | atributos de `mk_planos_acesso` | Parcial quando o plano permanece no catálogo | Derivação determinística |
| Modalidade anterior e atual | Evidências pré-importadas | atributos/tipo do plano | Parcial; sem contrato normalizado confirmado | Derivação a validar |
| Mesh anterior e atual | Evidências pré-importadas | plano e composição | Parcial; não normalizado | Derivação a validar |
| Adicionais anteriores e atuais | Evidências pré-importadas | composição do plano/itens | Parcial; histórico de composição não comprovado | Indisponível para automação integral |
| Valor recorrente anterior e novo | Evidências pré-importadas | delta histórico, catálogo e itens financeiros | Parcial; valor efetivo não é explícito nos dois lados | Derivação limitada |
| Data/hora da alteração | Evento importado | `mk_contratos_historicos.dt_hr` | Disponível | Explícita |
| Operador da alteração | Evento importado | `operador`, resolvível em parte para `usr_codigo` | Parcial | Explícita + derivação |
| Ticket presente | Evento importado | `mk_atendimento` | Disponível isoladamente | Explícita |
| Ticket ligado à mudança | Evento importado | Nenhuma chave encontrada | Indisponível deterministicamente | Apenas temporal |
| Autor do ticket e área de suporte | Evento importado | operadores e catálogos do atendimento | Disponível para o ticket | Explícita, mas sem vínculo com a mudança |
| Natureza administrativa/corretiva | Evidências pré-importadas | histórico/log e classificações | Não normalizada | Parcial |
| Fatura vinculada ao evento | Snapshot financeiro | item fiscal por contrato + plano, ou conta do contrato | Parcial | Determinística quando o item existe |
| Primeira fatura do novo valor | Snapshot financeiro | candidatos cronológicos | Não universalmente inequívoca | Parcial |
| Vencimento, status e pagamento | Snapshot financeiro | `mk_faturas` e históricos | Disponível | Explícita |
| Valor recorrente da fatura | Snapshot financeiro | item fiscal/composição | Parcial; fatura pode agregar itens | Derivação limitada |

## Exemplo real sanitizado

Um evento recente, sem identidade do cliente, demonstrou:

```text
contract_ref = 8c14a9e096
old_plan = 1000Mbps_LCE (catálogo: 99,90)
new_plan = 1000Mbps_1CAM-7D-LINKCEARA (catálogo: 134,80)
recorded_delta = 34,90
changed_at = 2026-08-26 08:19:24.067
invoice_id = 3750040
invoice_amount = 100,00
paid_amount = 100,00
paid_at = 2026-08-26 08:57:37.342
```

O exemplo comprova transição, item fiscal, fatura e pagamento. Também evidencia
por que preço de catálogo, item fiscal e total da fatura não devem ser tratados
como o mesmo conceito sem uma regra de composição.

## Gaps exatos

1. Não existe vínculo determinístico entre atendimento e alteração de plano.
2. Nem todo operador histórico resolve para `fr_usuario.usr_codigo` atual.
3. Há históricos sem plano anterior ou novo, e planos removidos do catálogo.
4. Não foram comprovados valores recorrentes efetivos anterior e novo em uma
   única fonte histórica; preço do catálogo não basta.
5. Mesh, modalidade e adicionais ainda precisam de normalização e histórico
   factual compatível com as evidências do Rules Engine.
6. A primeira fatura do novo valor não é identificável de forma inequívoca para
   todos os eventos.
7. Uma fatura pode agregar plano, adicionais, descontos e outros itens; seu
   total não equivale automaticamente à nova mensalidade.
8. Marcadores administrativos/corretivos e conflitos de autoria não estão
   normalizados para o contrato atual do Rules Engine.

## Recomendação arquitetural

O caminho futuro recomendado é:

```text
MK contratos + histórico explícito + planos
  -> descoberta de alteração
  -> fatos normalizados no Processing Engine
  -> CommercialEvent

MK atendimento
  -> contexto operacional independente
  -> vínculo determinístico somente quando uma chave futura for comprovada

MK itens fiscais + faturas + pagamentos
  -> snapshot financeiro factual
  -> Rules Engine
```

Para sincronização incremental, recomenda-se espelhar contratos, alterações de
plano, planos, itens fiscais, faturas e pagamentos. Consultas sob demanda não
são adequadas para reprocessamento auditável, grandes históricos ou preservação
de planos removidos. O espelho continua operacional; regras e classificações
permanecem no Rules Engine.

## Decisão operacional

Podemos eliminar a consulta manual do MK para descobrir quais contratos tiveram
Upgrade: **sim**.

Podemos eliminar toda consulta/complementação manual para processar e pagar o
Upgrade conforme o Rules Engine atual: **parcialmente**. Autoria pelo ticket,
valor recorrente efetivo e primeira fatura do novo valor ainda exigem contratos
adicionais ou revisão manual.

## Próxima missão recomendada

`MK-UPGRADE-DB-02` deve especificar, sem implementar regras novas:

1. contratos tipados read-only para as fontes comprovadas;
2. cursores incrementais por PK e timestamp;
3. modelo operacional para contrato, transição de plano, item fiscal, fatura e
   pagamento;
4. estratégia de snapshots para preservar planos removidos;
5. tratamento explícito dos gaps como `NOT_EVALUABLE` ou revisão manual;
6. investigação dirigida de uma chave determinística ticket ↔ mudança antes de
   qualquer atribuição automática ao autor do atendimento.

## MK-UPGRADE-DB-02 — contratos tipados e mirror comercial

Esta etapa implementa somente contratos de leitura e persistência operacional;
não executa sincronização nem cria `CommercialEvent`.

| DTO externo | SOURCE_PK / BUSINESS_KEY | Mutabilidade | Origem |
|---|---|---|---|
| `MkContract` | `codcontrato` | mutável | `mk_contratos` |
| `MkPlan` | `codplano` | mutável | `mk_planos_acesso` |
| `MkContractPlanChange` | `codcontratohist` | mutável/corrigível | `mk_contratos_historicos` |
| `MkContractOperation` | `codcontratooperacao` | catálogo | `mk_contratos_operacoes` |

O nome do plano, o login do operador e o timestamp são atributos, nunca
identidades. Os códigos 4 (Upgrade) e 5 (Downgrade) são constantes nomeadas,
mas o código bruto desconhecido continua preservado.

### Mirrors locais

| Tabela | Chave | Relações factuais por ID externo |
|---|---|---|
| `mk_contract_mirror` | `external_id = codcontrato` | cliente e plano atual |
| `mk_plan_mirror` | `external_id = codplano` | atributos do catálogo |
| `mk_contract_plan_change_mirror` | `external_id = codcontratohist` | contrato, plano anterior, plano novo e operador |

Não há FKs entre esses mirrors. Isso permite carga fora de ordem, preserva IDs
de planos removidos e aceita operadores ainda não resolvidos. A unicidade da PK
externa impede duplicação. Upserts comparam somente fatos: uma mudança isolada
de `source_last_seen_at` é `UNCHANGED`; correção factual da origem é `UPDATED`.

O `changed_by_operator_external_id`, quando resolvido univocamente em
`fr_usuario`, contém `str(usr_codigo)` e pode ser procurado em
`CollaboratorExternalIdentity(source="mk")`. Login não único ou ausente mantém
o ID nulo e exige resolução explícita; nenhum colaborador é criado aqui.

Timestamps PostgreSQL sem timezone são interpretados como `America/Fortaleza`
e persistidos em UTC, sem truncamento.

### Política de atendimento e financeiro

`ATTENDANCE_PLAN_CHANGE_LINK = TEMPORAL_ONLY` permanece uma barreira
arquitetural: nenhum campo ou repositório associa atendimento a alteração por
proximidade de horário, cliente, dia ou operador. A política codificada é
`temporal_link_rejected`.

Mirrors financeiros foram adiados. Contrato, plano e transição não precisam de
uma referência financeira para preservar seus fatos, e a auditoria classificou
valor histórico e pagamento como parciais. Modelá-los agora anteciparia a regra
de primeira fatura, expressamente fora desta etapa.

### Matriz MK → CommercialEvent atual

| Fato MK | Campo atual | Disponibilidade |
|---|---|---|
| `codcontratohist` | `external_reference` | DIRECT |
| `dt_hr` convertido para UTC | `occurred_at` | DIRECT |
| origem MK | `source` | DIRECT |
| planos anterior/novo e contrato | `raw_payload` | DIRECT |
| `usr_codigo` resolvido | colaborador | DERIVABLE; não há campo tipado atual |
| cliente do contrato | referência de cliente | NOT YET AVAILABLE como campo tipado |
| atendimento/ticket | ticket | NOT YET AVAILABLE; vínculo temporal rejeitado |
| valor recorrente anterior/novo | valor financeiro | NOT YET AVAILABLE |
| fatura/pagamento | evidência financeira | NOT YET AVAILABLE |

O `CommercialEvent` não foi alterado. A futura projeção pertence ao Motor de
Processamento e a interpretação 4/5 pertence ao Motor de Regras.

### Plano de sync futuro

Reutilizar `mk_sync_states` e `mk_sync_runs`, sem cursor novo:

- contratos: keyset `codcontrato > last_pk`, `ORDER BY codcontrato`, `LIMIT`;
- planos: keyset `codplano > last_pk`, `ORDER BY codplano`, `LIMIT`;
- alterações: keyset `codcontratohist > last_pk`, `ORDER BY codcontratohist`,
  `LIMIT`.

Como as três fontes são mutáveis, o sync incremental precisará também de uma
estratégia explícita de revisita/reconciliação. Esta missão prepara os upserts,
mas deliberadamente não escolhe nem executa essa estratégia.
