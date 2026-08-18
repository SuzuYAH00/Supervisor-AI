# CSAT — modelo factual do MVP

## Evidências documentais disponíveis

O CSAT é obtido de avaliações de clientes. As fontes operacionais confirmadas
são NPX, para ligações, e MK, para atendimentos via WhatsApp. Um atendimento
possui identificador externo, colaborador, canal, data/hora e pode possuir nota
CSAT. A documentação arquitetural também determina o cálculo de média.

## Modelo factual implementado

Cada avaliação persistida possui:

- `evaluation_id`: identificador da avaliação no arquivo de entrada;
- `external_reference`: referência auditável na fonte;
- `source`: origem do registro exportado;
- `collaborator_id`: colaborador associado;
- `channel`: canal informado pela fonte, opcional;
- `score`: nota decimal recebida;
- `evaluated_at`: instante da avaliação com timezone;
- `created_at`: instante técnico da persistência.

Esse contrato permanece disponível para avaliações factuais já importadas. As
exportações operacionais de MK e NPX também alimentam `CsatContact`, que
representa a população completa, inclusive contatos sem resposta:

- `source` e `external_reference` identificam o contato na origem;
- `collaborator_id` é resolvido por alias externo explícito;
- `external_operator_identity` preserva a identidade encontrada na exportação;
- `occurred_on` é a data civil do atendimento e determina a competência;
- `source_channel` registra se o fato veio da população Chat ou Phone;
- `score` é `null` quando não houve resposta e decimal quando a resposta é
  válida;
- `source_context` preserva contexto auditável da extração, como o setor MK.

`CsatEvaluation` continua representando somente respostas. `CsatContact` é a
fonte canônica usada para taxa de respondentes e composição automática da RV;
os contratos existentes não foram alterados nem reinterpretados.

A persistência legada de avaliações não pressupõe que `source` seja literalmente
`NPX` ou `MK`,
pois não existe contrato técnico confirmado para essas integrações. Um arquivo
local pode identificar, por exemplo, uma exportação dessas fontes.

## Importação local

`POST /imports/csat/csv` recebe `multipart/form-data`, no campo `file`, em
UTF-8. O cabeçalho exigido é:

```csv
evaluation_id,external_reference,source,collaborator_id,channel,score,evaluated_at
```

`channel` pode ficar vazio. Os demais campos são obrigatórios. `score` aceita
representação decimal finita com até seis casas, sem impor uma faixa de escala.
`evaluated_at` deve ser ISO 8601 com timezone.

A chave idempotente é `(source, external_reference)`. Reimportar os mesmos fatos
não cria nova avaliação. Reutilizar a identidade para fatos divergentes produz
conflito e não sobrescreve o histórico.

## Consultas

- `GET /csat/evaluations`: lista fatos, ordenados por `evaluated_at` e
  `evaluation_id` crescentes;
- `GET /csat/summary`: retorna quantidade e média aritmética geral, por
  colaborador e por canal.

Ambas aceitam `collaborator_id`, `start_date`, `end_date`, `source` e `channel`.
Datas usam `YYYY-MM-DD`, são inclusivas e filtram `evaluated_at`. Resultado vazio
é sucesso HTTP 200; sua média é `null`.

Notas e médias são strings decimais no HTTP. A agregação usa soma e contagem
decimais, sem passagem deliberada por `float` na Application Layer.

## Fontes operacionais auditadas

### MK — Chat

As exportações Financeiro e Técnico possuem o mesmo contrato e são partes da
mesma população de Chat. A separação decorre apenas de uma limitação da
interface de exportação e não cria modalidades ou regras diferentes.

- uma linha representa um protocolo;
- `Protocolo` é a referência externa idempotente;
- `Operador final` é resolvido exatamente por alias com `source=mk`;
- protocolos atribuídos a `MKBOT assistant` são excluídos;
- protocolos humanos com `Nota=-1` são contatos elegíveis sem resposta;
- notas de `0` a `5` são respostas válidas;
- `Setor` é preservado somente como contexto factual.

### NPX — Phone

- uma linha representa uma ligação;
- `Linkedid` é a referência externa idempotente;
- `Agente` é resolvido exatamente por alias com `source=npx`;
- todas as linhas pertencem ao denominador;
- `x/x/x` em P1/P2/P3 representa ausência de resposta;
- em resposta completa, P2 é a nota CSAT de `1` a `5`;
- P1 e P3 não recebem significado de domínio e não alteram a nota.

Não há correspondência aproximada de operadores. Alias ausente interrompe a
importação atômica em vez de atribuir o contato a outra pessoa.

## Indicador mensal factual

Por colaborador e competência:

```text
response_rate = valid_response_count / eligible_contact_count
raw_average = sum(valid_scores) / valid_response_count
competitive_score = raw_average * 2
```

Contatos sem resposta participam apenas do denominador. Quando não há contatos,
`response_rate`, `raw_average` e `competitive_score` são `null`; não se inventa
percentual ou elegibilidade. A modalidade competitiva vem do perfil do
colaborador. Assim, fatos ocasionais de outro canal não alteram a modalidade nem
entram no indicador daquele perfil.

A média normativa da equipe dá peso 1 a cada indicador individual elegível e é
truncada para duas casas decimais antes da comparação das faixas. Ela não é
ponderada pela quantidade de respostas.

## Limitação posterior ao MVP

O prazo normativo de resposta do MK é de até 30 minutos, mas há relatos de
avaliações realizadas aproximadamente até uma hora depois. A exportação atual
não oferece o instante da resposta de forma utilizável. O MVP não lê conversas,
não cria heurística e não invalida essas respostas. Uma automação futura deverá
validar esse caso por conteúdo e tempo da conversa sem alterar a regra factual
atual.

## Limites deliberados

- não existe conexão direta com banco MK nem integração externa NPX;
- os adapters leem somente os formatos XLSX auditados;
- a data da exportação representa a data civil do atendimento, sem inferência de
  horário ou timezone para a competência;
- correções divergentes para a mesma referência produzem conflito e não
  sobrescrevem o fato persistido;
- P1/P3 do NPX e textos de conversa MK permanecem fora do domínio.
