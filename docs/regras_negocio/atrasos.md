# Atrasos operacionais

## Separação factual

O domínio preserva três níveis independentes:

1. sessões e pausas brutas exportadas pelo NPX;
2. `DelayOccurrence`, derivado por regra normativa;
3. `DelayReview`, decisão humana append-only (`valid` ou `corrected`).

O agente externo é resolvido exatamente por `CollaboratorExternalIdentity` com
source `npx`. Não há fuzzy matching. Sessões e pausas usam referência
determinística construída de identidade externa, instantes, fila e, para
pausas, tipo. A referência da extração também é preservada.

Coberturas de `npx_work_sessions` e `npx_pauses` são declarações explícitas da
extração. A maior data encontrada não comprova cobertura.

## Pausas

Somente duas pausas geram atraso por duração:

- `Intervalo 20min`: até `20:59` é correto; `21:00` ou mais gera uma ocorrência;
- `Banheiro`: até `05:00` é correto; `05:01` ou mais gera uma ocorrência.

Cada pausa excedida gera uma ocorrência independente. `Reunião`,
`COL. SUPERVISOR`, `Intervalo 1 Hora`, `Intervalo 2 Horas` e tipos não
normatizados não geram atraso. O campo legado “Liberado pelo Supervisor” é
preservado como dado bruto, sem efeito normativo.

## Entrada

A regra confirmada compara o primeiro login do dia com o `planned_start`:
até o segundo `:59` do minuto planejado é correto e o minuto seguinte já é
atraso. Sessões posteriores não geram outro atraso; ausência de login é
ausência, não atraso. Não existe tolerância de ±35 minutos.

`DailyPlannedWorkScheduleFact` fornece a expectativa sem consultar o NPX. Um
override manual prevalece sobre grade explícita, que prevalece sobre expediente
padrão vigente no dia útil. Somente a primeira sessão é avaliada. Até
`planned_start:00:59` é pontual; o minuto seguinte produz `ENTRY`. Sem login é
ausência, não atraso. `PL` nunca produz `ENTRY`; `EX` sem slot explícito fica
não avaliável. Não existe tolerância de ±35 minutos.

## Revisão humana e Google Forms

Um atraso nasce contável. Sem revisão ou com decisão `valid`, continua
contando. Somente uma decisão humana explícita `corrected` o remove da contagem
mensal. O fato NPX nunca é alterado.

`EmployeeOccurrenceReport` registra apenas a declaração do colaborador. Um
relatório pode ser associado manualmente como evidência quando pertence ao
mesmo colaborador e data, mas sua existência não corrige nem aprova o atraso.
Motivo textual não é interpretado por IA. Múltiplos atrasos ou formulários não
são associados automaticamente.

## Integração com RV

A contagem persistida considera `DelayOccurrence` cuja decisão mais recente
não seja `corrected`. As faixas monetárias continuam no Rules Engine da RV.

A derivação automática para RV exige cobertura completa de
`npx_work_sessions`, `npx_pauses` e `planned_work_schedules`. Toda jornada
trabalhada sujeita a ponto também precisa estar resolvida. Cobertura ou jornada
incompleta bloqueia o fechamento, sem converter ausência de fatos em zero. O
override explícito `delay_facts` permanece compatível. A contagem soma `ENTRY`
e `PAUSE_DURATION` cuja decisão final não seja `corrected`.

Overrides operacionais passam pela mesma resolução usada no atraso de entrada:
alteram `planned_start/planned_end` somente no dia informado e preservam o
expediente padrão histórico.

## Consulta e revisão operacional

A consulta mensal apresenta o `DelayOccurrence`, seu fato NPX de origem, a
jornada efetiva quando o tipo é entrada, a revisão vigente e todas as
declarações do Forms do mesmo `collaborator_id + occurrence_date`. A
coincidência diária é apenas possível evidência e não cria vínculo automático.

Os estados da interface possuem esta semântica:

- `pending_review`: ainda não houve decisão, mas o atraso continua contando;
- `valid`: o supervisor revisou e manteve o atraso, que continua contando;
- `corrected`: a revisão vigente remove somente aquela ocorrência da contagem.

Revisões são append-only e a mais recente por `decided_at/id` é vigente. O fato
NPX não é atualizado ou apagado. O MVP registra `mvp-supervisor` como autoria
técnica da operação; esse valor não representa uma pessoa autenticada.
