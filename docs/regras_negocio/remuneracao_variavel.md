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

`collaborator_id`, usado pelo CSAT, e `operator_id`, usado pela Reincidência,
representam a mesma identidade operacional canônica. Não existe tradução entre
essas identidades.

Cada operador compete em exatamente uma modalidade: `chat` ou `phone`
(ligação). A modalidade é atributo factual do perfil operacional do colaborador,
determinado por sua função. Ela não é inferida do canal de uma avaliação ou de
um atendimento ocasional. Não se somam as modalidades.

O perfil mínimo atual persiste `collaborator_id` e `competitive_channel`. A
modalidade é estável no MVP; não há vigência nem atualização implícita. Uma
mudança futura deverá ocorrer por operação controlada e poderá evoluir o modelo
sem alterar a identidade canônica.

### Identidades externas do colaborador

`collaborator_id` permanece a identidade canônica interna. Identificadores ou
nomenclaturas fornecidos por sistemas externos são associados por meio do par
`(source, external_identity)`, que identifica exatamente um perfil operacional.
Um perfil pode possuir várias associações e o mesmo texto externo pode existir
em origens diferentes.

A associação preserva `source` e `external_identity` exatamente como recebidos:
não altera caixa, não remove espaços e não aplica busca aproximada. Integrações
futuras com MK, NPX, planilha de escala ou outras fontes deverão resolver essa
identidade antes de atribuir fatos ao colaborador. Uma associação ausente ou
ambígua falha explicitamente; não existe correspondência automática nem
sobrescrita silenciosa. O cadastro e a eventual alteração administrativa dessas
associações não possuem endpoint público nesta etapa.

As avaliações de Chat usam originalmente escala de 0 a 5 e as de Ligação,
escala de 1 a 5. Para competição, calcula-se primeiro a média bruta individual
do operador e multiplica-se esse resultado por 2. Assim, por exemplo, `4.6 × 2`
produz `9.2`, e a comparação da RV ocorre na escala final de 0 a 10.

A média competitiva de cada modalidade é calculada em três passos:

1. média bruta individual de cada operador participante;
2. normalização de cada média individual por `× 2`;
3. média aritmética das médias normalizadas dos operadores.

Cada operador possui peso 1. Não se usa média ponderada pela quantidade de
avaliações. A nota do operador e a média normativa recebidas pelo cálculo devem
pertencer à modalidade competitiva registrada em seu perfil.

O componente exige ao menos 20 dias trabalhados na competência. Com 20 dias ou
mais, inclusive quando parte das férias foi vendida, a participação é integral.
Não existe proporcionalidade monetária. Além da presença, Chat exige taxa de
respostas de ao menos `40%` e Ligação exige ao menos `50%`. Quem não satisfaz
presença ou cobertura mínima não participa da média competitiva da modalidade.

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
| Ouro | média final igual a `10.00` | R$ 800,00 |
| Prata | nota maior ou igual à média do canal mais `0.10` | R$ 200,00 |
| Bronze | nota maior ou igual à média do canal mais `0.05` | R$ 100,00 |

Apenas a maior faixa atingida é aplicada. A escala original confirmada de
Ligação é 1 a 5 e sua normalização produz máximo competitivo `10.00`. O Rules
Engine puro continua recebendo o máximo como entrada explícita; a futura
composição factual deverá fornecer `10.00` a partir desta regra normativa, sem
inferi-lo das avaliações observadas.

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

A média normativa usada pela RV é a média aritmética das taxas individuais dos
participantes, com peso 1 por operador. Por exemplo, taxas de `10%`, `14%` e
`18%` produzem média normativa de `14%`. O agregado operacional
`total_occurrences / total_eligible_attendances` possui outra semântica e não é
a referência competitiva da RV.

Somente operadores com ao menos 20 dias trabalhados na coorte entram nessa
média. Quando a média normativa dos participantes fica acima de `20%`, a trava
coletiva impede premiação de Reincidência para todos, ainda que uma diferença
individual alcançasse faixa.

## Elegibilidade por componente

A referência de 20 dias do CSAT é aplicada aos dias trabalhados no próprio mês
da competência. Um operador com menos de 20 dias fica `not_eligible` nesse
componente.

Reincidência é baseada na coorte do mês anterior e sua elegibilidade usa os dias
trabalhados nesse mês anterior. Assim, na RV de julho um operador pode receber
Reincidência da coorte de junho mesmo estando de férias em julho. Já a RV de
agosto usa a coorte de julho; se o operador não atingiu 20 dias trabalhados em
julho, ele não participa desse componente em agosto.

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

A composição usa diretamente `penalizable_absence_days` do slice de presença.
Atualmente `A`, `F` e `OF` alimentam esse total. `B.H` reduz a quantidade
potencial de dias trabalhados, mas é ausência não penalizável e não gera esse
desconto.

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

## Composição factual atual

O caso de uso de composição recebe a competência e os atrasos ainda explícitos.
Ele consulta automaticamente:

- perfil/modalidade competitiva do colaborador;
- presença da competência para CSAT e ausências;
- presença de `M-1` para Reincidência.
- fatos mensais de CSAT;
- resumo canônico de Reincidência da coorte `M-1`, limitado à fonte oficial MK.

As médias são calculadas somente entre participantes elegíveis. A composição
não lê XLSX nem reinterpreta códigos: consome a consolidação canônica de
presença. Resultado negativo continua preservado. A Reincidência automática só
é derivada quando a evidência persistida de cobertura do MK alcança o fim da
janela normativa; cobertura ausente ou insuficiente interrompe a composição,
sem produzir taxa zero ou resultado parcial. Operadores sem população elegível
recebem taxa `null`.

Fatos explícitos de Reincidência permanecem como override interno compatível.
Quando ausentes, a Application consulta a cobertura, obtém o resumo canônico e
apenas projeta numerador, denominador e taxa para a competição. Presença, média
com peso igual, trava coletiva e faixas continuam na composição e no Rules
Engine. A fonte factual de atrasos permanece entrada mensal explícita.

Respostas do Google Forms são persistidas separadamente como declarações do
colaborador. Elas não corrigem atrasos nem alteram descontos ou a RV sem uma
decisão humana explícita, que permanece fora do escopo atual.

## Fora do escopo atual

Não estão implementados persistência do resultado de RV, endpoint, frontend,
fonte de atrasos, integração com folha, postagem no Ledger, penalização de Red
Flag, Qualidade, scheduler, fila, autenticação ou recomendação por IA.
