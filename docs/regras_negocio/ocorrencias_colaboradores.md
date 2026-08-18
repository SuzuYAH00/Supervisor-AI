# Ocorrências declaradas por colaboradores

## Fato operacional

Uma resposta do Google Forms registra somente que o colaborador declarou uma
ocorrência. O fato preserva a identidade canônica resolvida, a identidade
externa apresentada pela fonte, o instante do envio, a data civil declarada e
o texto original do motivo.

A fonte interna é `google_forms_employee_occurrences`. A identidade externa é
resolvida exclusivamente por `CollaboratorExternalIdentity`; não existe busca
aproximada ou associação por semelhança.

## Contrato da exportação

A aba `Respostas ao formulário 1` deve começar com as colunas:

1. `Carimbo de data/hora`;
2. `Técnico de Suporte`;
3. `Data - (DD/MM/AA)`;
4. `Motivo Ocorrência`;
5. `Pontuação`.

O carimbo é interpretado no timezone operacional `America/Fortaleza`. A data
da ocorrência aceita exclusivamente `DD/MM/AA` ou `DD/MM/AAAA`; ano com dois
dígitos significa `20AA`. Texto adicional, horário, ano ausente e outros
separadores são rejeitados sem tentativa de correção.

`Pontuação` não representa aprovação e não é interpretada pelo Supervisor AI.
O texto do motivo também não é classificado ou interpretado.

## Importação parcial e identidade

A identidade técnica é um hash determinístico da fonte, da identidade externa
e do instante do envio. O carimbo participa da identidade, mas isoladamente
não é tratado como identificador garantido pelo Google Forms.

Uma resposta idêntica reimportada é idempotente. A mesma identidade técnica
com fatos divergentes gera `conflicting_occurrence` e não sobrescreve o fato
persistido.

Linhas inválidas não impedem a importação das demais. O relatório distingue
linhas importadas, idempotentes, rejeitadas e conflitantes, preservando número
da linha, identidade externa, código do problema e valor inválido relevante.

## Relação com atrasos e RV

Uma ocorrência pode futuramente ser apresentada ao supervisor ao lado dos
atrasos do mesmo colaborador e data. Essa coincidência não estabelece vínculo
individual quando houver múltiplos fatos e nunca representa aprovação.

A existência da resposta:

- não corrige atraso;
- não elimina desconto;
- não altera a RV;
- não aprova justificativa;
- não executa interpretação por IA.

Somente uma decisão humana futura, explícita e auditável, poderá marcar um
atraso como corrigido. O fato original importado não será apagado ou alterado.
