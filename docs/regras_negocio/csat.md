# CSAT — modelo factual do MVP

## Evidências documentais disponíveis

O CSAT é obtido de avaliações de clientes. As fontes de negócio previstas são
NPX, para ligações, e MKBot, para atendimentos via WhatsApp. Um atendimento
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

A persistência não pressupõe que `source` seja literalmente `NPX` ou `MKBot`,
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

## Lacunas e limites deliberados

A documentação atual não define:

- escala mínima ou máxima da nota;
- se todas as fontes usam a mesma escala;
- regra de elegibilidade de uma avaliação;
- metas, cortes, bônus de RV ou classificação qualitativa;
- tratamento de correções retroativas na fonte;
- contrato técnico direto com NPX ou MKBot.

Por isso, esta versão não valida faixa, não compara colaboradores, não
classifica resultados e não alimenta RV. Essas decisões exigem documentação de
negócio posterior.
