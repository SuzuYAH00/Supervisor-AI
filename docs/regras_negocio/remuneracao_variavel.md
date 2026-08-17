# Remuneração Variável operacional mensal

## Estado da política

A política vigente de Remuneração Variável (RV) operacional possui cálculo
normativo determinístico para CSAT, Reincidência, atrasos e
ausências/atestados.

Qualidade foi descontinuada e não participa da política atual. Seu antigo valor
não é redistribuído. O máximo dos componentes positivos vigentes é
R$ 1.600,00:

- CSAT: até R$ 800,00;
- Reincidência: até R$ 800,00.

A regra está implementada no Rules Engine como cálculo puro. Ainda não existe
integração de fatos, persistência de competência, endpoint ou lançamento de RV
no Ledger.

## Separação da remuneração comercial

A remuneração comercial já existente calcula créditos de upgrades e adicionais
vinculados a Commercial Events. A RV operacional é mensal, pertence a um
colaborador e consome indicadores e ocorrências de jornada.

Os dois domínios permanecem separados. O cálculo de RV não reutiliza evento
comercial fictício e não posta no Ledger atual.

## Competência mensal

Uma competência preserva referências factuais distintas:

- `competence_month`: mês civil da RV;
- `csat_reference_month`: o próprio mês da competência;
- `recurrence_cohort_month`: mês civil imediatamente anterior;
- `attendance_reference_month`: o próprio mês da competência, para atrasos e
  ausências/atestados.

Exemplo para a competência de agosto:

- CSAT de agosto;
- Reincidência da coorte de julho, observada durante a janela normativa de 30
  dias;
- atrasos e ausências/atestados de agosto.

O cálculo de RV consome resultados factuais de CSAT e Reincidência. Ele não
recalcula avaliações CSAT nem repete elegibilidade, pareamento ou taxa de
Reincidência.

## Estados dos componentes

Cada componente preserva um dos estados:

- `eligible`: o componente participa; seu valor pode ser positivo ou R$ 0,00;
- `not_eligible`: o componente não participa e contribui com R$ 0,00;
- `not_evaluable`: faltam fatos necessários e nenhum valor pode ser concluído.

Um componente `not_eligible` é diferente de um componente `eligible` que não
atingiu faixa e recebeu R$ 0,00. Se algum componente necessário estiver
`not_evaluable`, o valor total e a flag não são materializados.

## CSAT

Cada operador compete em exatamente um canal: `chat` ou `phone` (ligação). Não
se somam os dois canais. A nota do operador e a média normativa recebidas pelo
cálculo devem pertencer ao canal competitivo informado.

O componente exige ao menos 20 dias trabalhados na competência. Com 20 dias ou
mais, inclusive quando parte das férias foi vendida, a participação é integral.
Não existe proporcionalidade monetária.

### Chat

As faixas são avaliadas da maior para a menor:

| Faixa | Regra | Valor |
|---|---|---:|
| Ouro | nota maior ou igual a `9.50` | R$ 800,00 |
| Prata | nota maior ou igual à média do canal mais `0.10` | R$ 200,00 |
| Bronze | nota maior ou igual à média do canal mais `0.05` | R$ 100,00 |

Apenas a maior faixa atingida é aplicada.

### Ligação

| Faixa | Regra | Valor |
|---|---|---:|
| Ouro | nota igual à nota máxima factual do canal/escala | R$ 800,00 |
| Prata | nota maior ou igual à média do canal mais `0.10` | R$ 200,00 |
| Bronze | nota maior ou igual à média do canal mais `0.05` | R$ 100,00 |

Apenas a maior faixa atingida é aplicada. Como o contrato factual de CSAT atual
não informa a nota máxima da escala de ligação, o Rules Engine exige esse valor
como fato explícito. Sem ele, o componente fica `not_evaluable`; nenhuma
constante de escala é presumida.

## Reincidência

Menor taxa é melhor. O cálculo recebe a taxa factual do operador e a média
normativa da população correspondente, ambas representadas como razões
decimais. A diferença é calculada em pontos percentuais:

```text
diferenca = media_populacao - taxa_operador
```

| Faixa | Regra | Valor |
|---|---|---:|
| Ouro | diferença maior ou igual a 12 p.p. | R$ 800,00 |
| Prata | diferença maior ou igual a 5 p.p. | R$ 200,00 |
| Bronze | diferença maior ou igual a 3 p.p. | R$ 100,00 |

Por exemplo, média `0.20` e taxa `0.17` produzem diferença `0.03`, ou 3 pontos
percentuais, e faixa Bronze. Não se aplica redução relativa de 3% sobre a média.

Apenas a maior faixa atingida é aplicada.

## Elegibilidade por componente

A referência de 20 dias é aplicada ao CSAT da competência atual. Um operador
com menos de 20 dias fica `not_eligible` nesse componente.

Reincidência é baseada na coorte do mês anterior e recebe elegibilidade própria.
Assim, um operador de férias no mês atual pode não participar do CSAT e ainda
receber integralmente Reincidência por atendimentos elegíveis da coorte
anterior.

Não há regra global que zere a RV inteira pela indisponibilidade de um único
componente, nem proporcionalidade pelo número de dias trabalhados.

## Descontos

### Atrasos na competência

| Quantidade | Desconto |
|---:|---:|
| 0 | R$ 0,00 |
| 1 a 2 | -R$ 25,00 |
| 3 a 9 | -R$ 50,00 |
| 10 ou mais | -R$ 250,00 |

### Ausências/atestados na competência

| Dias | Desconto |
|---:|---:|
| 0 | R$ 0,00 |
| 1 | -R$ 50,00 |
| 2 | -R$ 75,00 |
| 3 ou mais | -R$ 250,00 |

As faixas não são cumulativas dentro da mesma categoria. Descontos de
categorias diferentes são somados ao resultado.

## Resultado e flags

```text
RV = CSAT + Reincidencia + desconto_atrasos + desconto_ausencias
```

Não existe piso zero. Um resultado negativo é preservado, mas não representa
dívida, desconto salarial ou valor a cobrar do colaborador.

| Resultado | Flag |
|---:|---|
| maior que zero | `green` |
| igual a zero | `white` |
| menor que zero | `red` |

A flag é somente classificação derivada do resultado da RV. Penalizações
adicionais de Red Flag permanecem fora do escopo.

## Precisão

Notas, taxas e valores monetários usam `Decimal`. Valores monetários normativos
preservam centavos e não passam por `float`. A política não introduz
arredondamento monetário ou proporcionalidade.

## Relação com Qualidade

O processo histórico de Qualidade foi descontinuado. Qualidade não é avaliada,
não recebe zero, não bloqueia a competência e não tem seu antigo valor
redistribuído entre CSAT e Reincidência.

Um futuro mecanismo de auditoria deverá ser especificado separadamente e não
altera automaticamente esta política.

## Relação com o Ledger

O Ledger atual possui vínculo obrigatório com Commercial Event e foi desenhado
para remuneração comercial por evento. Isso não representa naturalmente uma
competência mensal de RV.

Por essa razão, esta etapa não cria lançamento, saldo, dívida ou desconto
salarial. Uma integração financeira futura deverá definir identidade
idempotente da competência, referência da política e origem não comercial antes
de qualquer postagem.

## Bloqueios de integração

O cálculo puro está fechado, mas o sistema ainda não possui todos os fatos
necessários para executá-lo automaticamente:

- atribuição comprovada de um único canal competitivo a cada operador;
- nota máxima factual da escala de ligação;
- média normativa de CSAT por canal e regra da população correspondente;
- média normativa da população de Reincidência a ser usada pela RV;
- fonte factual de dias trabalhados, atrasos e ausências/atestados;
- elegibilidade factual de Reincidência para a competência de RV.

Esses dados são entradas explícitas da regra e não são inventados pelo Rules
Engine.

## Fora do escopo atual

Não estão implementados persistência de RV, endpoint, frontend, integração com
folha, postagem no Ledger, penalização de Red Flag, Qualidade, scheduler, fila,
autenticação ou recomendação por IA.
