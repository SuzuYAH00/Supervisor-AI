# Presença e escala operacional

## Fonte e recorte suportado

O formato normativo inicial é o workbook de escala utilizado a partir de
abril de 2026. Formatos anteriores não são aceitos. A fonte interna estável é
`attendance_sheet`; o nome encontrado na planilha é resolvido exatamente por
`CollaboratorExternalIdentity` antes de qualquer fato ser atribuído ao
`collaborator_id` canônico. Não existe associação aproximada ou por
similaridade.

A data da célula diária determina a competência. Uma célula cuja data esteja
fora do mês indicado pela aba é ignorada. Fórmulas e consolidações legadas não
são fonte normativa: os resultados são derivados novamente dos códigos das
células diárias.

## Fato diário

Cada célula diária não vazia produz um fato rastreável com colaborador, data,
competência, código bruto, fonte, aba, célula e referência externa. A
reimportação do mesmo conteúdo é idempotente. A mesma referência ou o mesmo
par colaborador/data com conteúdo divergente produz conflito e não sobrescreve
o histórico silenciosamente.

## Classificação dos códigos

| Categoria | Códigos |
|---|---|
| dia trabalhado | `P`, `PS`, `PD`, `PF`, `FT`, `EX`, `PL` |
| ausência penalizável para RV | `A`, `F`, `OF` |
| ausência não penalizável | `B.H` |
| dia não trabalhado sem penalização definida | `FE`, `D`, `D.O`, `DF` |

Códigos presentes na origem sem semântica normativa confirmada são preservados
como não classificados. Eles não recebem significado monetário por inferência.

“Ausência para fins de presença” não significa necessariamente “ausência
penalizável para RV”. `B.H` é o principal exemplo: representa descanso por
horas previamente trabalhadas, não conta para os 20 dias e não aumenta
`absence_days` da RV.

## Consolidação mensal

`worked_days` é a quantidade de fatos classificados como dia trabalhado. A
regra factual mínima é:

```text
meets_minimum_worked_days = worked_days >= 20
```

Não existe proporcionalidade. A consolidação também informa separadamente os
dias de ausência penalizável e não penalizável. A composição da RV usa o mês da
competência para CSAT e descontos por ausência, e `M-1` para a elegibilidade de
Reincidência. Ela ainda respeita os demais requisitos próprios dos indicadores.

## Expediente padrão e jornada planejada

O expediente padrão é versionado por vigência. O cadastro mutável da aba
`DADOS` não pode reescrever competências anteriores; snapshots mensais
explicitamente disponíveis preservam o período a que pertencem. Vigências do
mesmo colaborador não podem se sobrepor.

A jornada diária é um fato separado do status de presença. A resolução segue:

1. override manual auditável do dia;
2. slot explícito da grade de fim de semana ou feriado;
3. expediente padrão vigente em dia útil normal.

As grades explícitas admitem `08:00–14:00`, `11:00–17:00` e `14:00–20:00`.
Uma jornada diferente do padrão é expediente alternativo, não atraso. `EX`
exige slot explícito; `PL` preserva presença, mas supervisor não bate ponto no
NPX e não é avaliado para atraso de entrada.

Quando a grade mensal confirma trabalho de fim de semana/feriado, mas não há
slot exato para o alias, a jornada fica explicitamente não resolvida. Não há
fallback para o padrão. A cobertura de `planned_work_schedules` somente avança
por declaração explícita da extração; a maior data encontrada não é cobertura.

O parser suporta apenas o formato de abril/2026 em diante e usa a data real das
células e dos blocos. Datas fora da competência são ignoradas. Alias é sempre
resolvido por `CollaboratorExternalIdentity`, sem aproximação.
