# Reincidência — regra factual do MVP

## Evidências operacionais

A regra foi confirmada pela operação e confrontada com a planilha local
`2026.8 Reincidencia Agosto.xlsx`. A planilha possui as abas `Dados`,
`Aprovação de Tickets ALL`, `Aprovação de Tickets` e `Reincidencia` e evidencia:

- universo geral e subconjunto técnico de atendimentos;
- cliente identificado por `Codigo Cliente`;
- protocolo individual;
- data de abertura;
- operador que encerrou o atendimento, usado como responsável operacional;
- atendimento posterior e protocolo relacionado;
- quantidade de reincidências;
- denominador de atendimentos técnicos;
- taxa calculada como reincidências divididas por atendimentos técnicos.

A planilha foi usada como evidência e não como arquitetura executável. Suas
fórmulas também consideram uma lista de operadores, mas a decisão vigente
determina que operador é dimensão de atribuição, não critério técnico.

## Fato de atendimento

O fato persistido possui:

- `attendance_id`: identificador interno fornecido no arquivo;
- `external_reference`: protocolo ou referência auditável na fonte;
- `source`: origem do arquivo;
- `customer_code`: identidade externa usada para relacionar contatos;
- `operator_id`: responsável pelo atendimento;
- `channel`: canal factual do contato;
- `occurred_at`: instante do atendimento com timezone;
- processo;
- classificação de abertura;
- classificação de encerramento;
- `created_at`: timestamp técnico da persistência.

Processo e classificações preservam código opcional e descrição. Código e
descrição formam juntos a identidade quando ambos existem. Classificações sem
código são válidas e não recebem código artificial.

## Elegibilidade técnica

Um atendimento é elegível somente quando as três condições são verdadeiras:

```text
processo elegível
AND classificação de abertura elegível
AND classificação de encerramento elegível
```

O processo elegível é `01 - Atendimento Suporte`.

### Classificações de abertura elegíveis

- `001 - Sem acesso a internet`
- `002 - Lentidão`
- `003 - Alteração de Senha/SSID`
- `004 - Problemas na TV`
- `005 - Problemas em VPN`
- `006 - Problemas em Jogos`
- `007 - Problemas Impressora`
- `008 - Problemas no IPTV`
- `009 - Problemas no WiFi`
- `010 - Analise de Quedas PPPoE`
- `011 - Velocidade do Plano`
- `012 - Entrga/Config. Roteador`
- `013 - Quedas de conexão`
- `014 - Mudança de Endereço`
- `015 - Mudança de Ponto`
- `016 - Melhoria de sinal`
- `017 - Entrega de Cabo`
- `018 - Aplicativo LINKCE`
- `019 - Sugestão/Reclamação`
- `020 - Linkvideo`
- `021 - Solicitação Boleto/Pix`
- `024 - Relatório de Conexão`
- `030 - Alteração de plano`
- `030 - Link PG Cartão`
- `106 - Pesquisa Satisfação`
- `NPS Detratores`
- `NPS Passivos`
- `NPS Promotores`
- `Dúvidas`

`014 - Problemas em Jogos` não pertence à relação vigente. A identidade válida
com código `014` é `014 - Mudança de Endereço`. O texto operacional, inclusive
`Entrga`, é preservado sem correção silenciosa.

### Classificações de encerramento elegíveis

- `001 - Dispositivo Cliente`
- `002 - Fonte do equipamento`
- `003 - Alcance do Wi-Fi`
- `004 - Problema no Roteador/ONT`
- `010 - Orientação Redes 2G/5G`
- `011 - Orientação Sobrecarga`
- `012 - Orientação Cabeamento`
- `013 - Orientação Velocidade`
- `019 - Dúvidas Linkvideo`
- `020 - Alteração SSID/Senha`
- `021 - Alteração Criptografia`
- `022 - Alteração de Tecnologia`
- `023 - Habilitar/Desab WPS`
- `024 - Habilitar/Desab IPv6`
- `025 - Config. Redirecionamento`
- `026 - Config. DMZ`
- `028 - Reprovisionamento`
- `029 - Roteador Reiniciado`
- `030 - Rota`
- `031 - Falha no link`
- `032 - Rede Interna Cliente`
- `033 - Elétrica do Cliente`
- `034 - Aplicação de Terceiros`
- `035 - Internet compartilhada`
- `036 - Roteador Resetado`
- `041 - Problema Conector RJ45`
- `002 - Internet compartilhada`
- `009 - Aplicação de Terceiros`
- `010 - Rota`
- `012 - Fonte do equipamento`
- `013 - Elétrica do Cliente`
- `015 - Config. Roteador`
- `016 - Roteador Resetado`
- `014 - Rede Interna Cliente`
- `023 - Instalação 2° Roteador`
- `033 - Problema Conector RJ45`
- `039 - Desligou equipamento`
- `045 - Perda de Pacote`

As classificações retiradas `014 - Orientação Desbloqueio`, `015 - Dúvidas APP
Usabilidade`, `016 - Dúvidas APP Login/Senha` e `017 - Dúvidas Mud.Plano` não
são elegíveis. `018 - Dúvidas Mud.Endere/Ponto` permanece conservadoramente fora
até decisão operacional posterior.

## Pareamento e janela

Atendimentos elegíveis são agrupados por `customer_code` e ordenados por
`occurred_at`, com `attendance_id` como desempate técnico determinístico. Apenas
atendimentos elegíveis consecutivos formam candidatos.

A janela usa datas civis. O retorno é reincidente quando:

```text
0 <= data_retorno - data_original <= 30 dias
```

O limite de 30 dias é inclusivo e não é convertido em 720 horas. Canal não
participa da decisão: ligação e WhatsApp podem formar o mesmo par.

Na cadeia `A -> B -> C`, são produzidos os pares `A -> B` e `B -> C`. Não é
produzido `A -> C`.

## Atribuição e coorte

A ocorrência pertence ao operador do atendimento original. O período também é
o mês civil do atendimento original, ainda que o retorno aconteça no mês
seguinte.

Uma coorte mensal só pode ser consultada como fechada quando a observação cobre
o último dia do mês mais 30 dias. A API exige `observed_through` e rejeita uma
janela incompleta.

Para uso automatizado, o calendário não é evidência suficiente de observação.
O banco precisa possuir uma declaração persistida de cobertura do dataset e da
fonte cujo `covered_through` alcance o fim da janela. A maior data encontrada em
`occurred_at` não representa cobertura: uma fonte pode estar completa mesmo em
um dia sem atendimentos e pode conter um registro recente apesar de possuir
lacunas anteriores.

Cada declaração de cobertura preserva dataset, fonte, referência da extração,
data garantida e instante de registro. As declarações são append-only. Uma nova
extração pode avançar a cobertura efetiva; declarações com data anterior ficam
registradas para auditoria, mas não fazem o watermark regredir. Sem declaração,
a cobertura é desconhecida e a coorte não é fechada automaticamente.

Para a competição mensal de RV, a fonte oficial é `mk`. Chat e ligação já são
consolidados como tickets no relatório mensal do MK; esta etapa não combina
outras fontes. A derivação automática exige que a cobertura do dataset de
atendimentos da fonte MK alcance o fim integral da janela da coorte.

## Taxa

```text
taxa_reincidencia = reincidências / atendimentos técnicos elegíveis
```

Atendimentos gerais ou inelegíveis não entram no denominador. Quando não há
atendimento elegível, a taxa é `null`, seguindo a convenção factual já usada
para agregações sem população no projeto.

## Importação local e idempotência

`POST /imports/recurrence/attendances/csv` recebe UTF-8 em
`multipart/form-data`, campo `file`. O cabeçalho é:

```csv
attendance_id,external_reference,source,customer_code,operator_id,channel,occurred_at,process_code,process_description,opening_code,opening_description,closing_code,closing_description
```

Códigos de classificação podem ficar vazios; descrições são obrigatórias.
`occurred_at` deve ser ISO 8601 com timezone.

A chave idempotente é `(source, external_reference)`. Reimportar o mesmo fato
não duplica atendimento. Reutilizar a identidade com conteúdo divergente gera
conflito e não sobrescreve o registro.

Resultados de reincidência não são persistidos nesta versão: são derivados pelo
Rules Engine a partir dos fatos. Assim, reimportação idempotente também não cria
resultado duplicado.

O importador pode receber, separadamente dos registros, `source`,
`covered_through` e uma referência auditável da extração. Essa declaração
significa que a origem garante ter fornecido todos os atendimentos necessários
até a data informada. Ela nunca é inferida do conteúdo do CSV. Reutilizar a
mesma referência com a mesma declaração é idempotente; reutilizá-la com outra
data gera conflito explícito.

## Consultas

- `GET /recurrence/attendances`: fatos filtráveis por operador, cliente, fonte,
  canal e período inclusivo de `occurred_at`;
- `GET /recurrence/summary`: resultado de uma coorte mensal fechada, com total
  elegível, ocorrências, taxa e agrupamento por operador.

O resumo aceita `reference_month=YYYY-MM`, `observed_through=YYYY-MM-DD` e
filtros opcionais de operador, fonte e canal. Filtros dimensionais selecionam os
atendimentos originais da coorte; o contato posterior pode ter outro canal ou
operador.

## Decisões de negócio pendentes

- semântica definitiva de `018 - Dúvidas Mud.Endere/Ponto`;
- contrato técnico direto e garantias de identidade de NPX, MKBot e MK
  Workspace;
- tratamento de fontes que forneçam dois atendimentos do mesmo cliente com o
  mesmo instante exato;
- política para correções e exclusões retroativas na fonte.

## Fora do escopo

Esta versão não implementa frontend, meta, ranking, classificação de operador,
alerta, recomendação, IA ou integração direta com sistemas externos. A
Application fornece a taxa mensal coberta à composição da RV, sem persistir o
resultado derivado.
