# Arquitetura Frontend do Supervisor AI

## 1. Objetivo

O frontend do Supervisor AI será a camada de interação entre os gestores e as informações processadas pelo sistema.

Seu objetivo principal é transformar dados operacionais em uma experiência simples, rápida e orientada à tomada de decisão.

O frontend não deve apenas exibir informações, mas ajudar o supervisor a responder perguntas importantes da operação.

Exemplos:

- O que precisa da minha atenção hoje?
- Quem está abaixo da média?
- Qual problema está aumentando?
- Qual ação devo tomar?

---

# 2. Princípios da interface

## Informação antes de complexidade

A interface deve priorizar informações relevantes.

O supervisor não deve precisar navegar por várias telas para encontrar problemas importantes.

---

## Decisão rápida

A primeira tela deve permitir uma compreensão rápida da operação.

Objetivo:

"Em 30 segundos, entender como a equipe está."

---

## Dados antes de opiniões

Todas as recomendações devem possuir origem em dados.

Exemplo:

Não informar:

"João precisa melhorar."

Informar:

"João apresentou CSAT 0,4 abaixo da média da equipe nos últimos 7 dias."

---

# 3. Estrutura inicial de telas

## Dashboard principal

Tela inicial do supervisor.

Objetivo:

Apresentar a situação atual da operação.

Informações possíveis:

- Indicadores gerais;
- Alertas;
- Evolução recente;
- Pendências;
- Destaques positivos.

---

# 4. Módulo de indicadores

Responsável por acompanhar métricas operacionais.

Indicadores:

- CSAT;
- Reincidência;
- Qualidade;
- Cancelamentos;
- Upgrades;
- Extras.

Possibilidades:

- Filtrar por período;
- Filtrar por equipe;
- Filtrar por colaborador;
- Comparar evolução.

---

# 5. Módulo de colaboradores

Responsável pela análise individual.

Informações:

- Nome;
- Equipe;
- Indicadores atuais;
- Histórico;
- Pontos positivos;
- Pontos de atenção.

Exemplo:

```
Colaborador: João

CSAT:
Atual: 9,4
Média equipe: 9,7

Reincidência:
Atual: 12%
Média equipe: 8%

Sugestão:
Avaliar atendimentos técnicos recentes.
```

---

# 6. Módulo de pagamentos

Responsável por acompanhar valores destinados aos colaboradores.

Exibir:

- Upgrade;
- RV;
- Extras;
- Total.

Exemplo:

```
João

Upgrade:
R$ 299,90

RV:
R$ 400,00

Extras:
R$ 180,00

Total:
R$ 879,90
```

---

# 7. Módulo de upgrades

Responsável pelo acompanhamento das vendas realizadas.

Informações:

- Cliente;
- Operador;
- Plano anterior;
- Novo plano;
- Valor;
- Status.

Estados:

- Alteração pendente;
- Cliente aguardando pagamento;
- Pago;
- Finalizado.

---

# 8. Módulo de extras

Responsável pelo acompanhamento das horas extras.

Informações:

- Colaborador;
- Data;
- Horário;
- Tipo;
- Valor;
- Validação.

Validações:

- Conflito com jornada;
- Intervalo;
- Aprovação.

---

# 9. Módulo de cancelamentos

Responsável por análise de perda de clientes.

Informações:

- Quantidade;
- Motivos;
- Padrões encontrados;
- Clientes recentes;
- Tendências.

Objetivo:

Encontrar causas e oportunidades de melhoria.

---

# 10. Central de alertas

Uma das principais funções do Supervisor AI.

Exemplos:

## Alerta de desempenho

"Operador abaixo da média de CSAT há 7 dias."

---

## Alerta operacional

"Quantidade de cancelamentos aumentou 20% comparado ao período anterior."

---

## Alerta financeiro

"Existem upgrades aguardando confirmação de pagamento."

---

# 11. Assistente de inteligência artificial

O frontend deverá possuir uma área onde o supervisor possa conversar com a IA.

Exemplos:

Pergunta:

"Qual foi o principal motivo de cancelamento esse mês?"

Resposta:

"A principal causa foi inadimplência, representando X% dos cancelamentos analisados."

---

Pergunta:

"Quem precisa de acompanhamento?"

Resposta:

"3 colaboradores apresentam queda de desempenho comparado à média da equipe."

---

# 12. Perfis de acesso

## Supervisor

Visualização:

- Sua equipe;
- Seus indicadores;
- Seus pagamentos.

---

## Gerente

Visualização:

- Todas as equipes;
- Comparações;
- Relatórios gerais.

---

## Administrador

Visualização:

- Configurações;
- Usuários;
- Parâmetros.

---

# 13. Evolução futura

Possíveis evoluções:

- Aplicativo mobile;
- Notificações;
- Dashboards personalizados;
- Recomendações automáticas;
- Ações executadas pela IA.

---

# 14. Observação

A primeira versão do frontend deve priorizar simplicidade.

O objetivo inicial não é criar uma ferramenta complexa, mas entregar uma visão operacional rápida e confiável para o supervisor.

---

# 15. Implementação do MVP

O frontend utiliza React, TypeScript strict, Vite e React Router. A organização
por feature separa transporte HTTP, validação runtime, hook, componentes e
página. Toda comunicação ocorre pela API do Supervisor AI, por meio do cliente
`fetch` centralizado.

As telas funcionais atuais são:

- Saúde do processamento;
- Resumo financeiro;
- Eventos comerciais;
- Timeline financeira por colaborador;
- Execuções de processamento.

## Listagem de execuções

`/processing-runs` consome `GET /processing-runs` automaticamente ao abrir. O
contrato público contém uma coleção mínima de execuções e `next_cursor`.
Campos internos, fases, warnings, Ledger e valores financeiros não atravessam
essa projeção.

A ordem dos itens é preservada exatamente como entregue pela API. O frontend
não calcula duração, indicadores, percentuais, totalizadores ou diagnóstico a
partir dos timestamps e status.

A paginação é keyset: o cursor recebido é opaco, enviado sem interpretação e
guardado somente no histórico local da tela para permitir retorno. Não existe
offset, total de páginas ou persistência em `localStorage`. Retry repete o
cursor solicitado; a transição limpa os dados anteriores; `AbortController` e
um ciclo ativo impedem atualizações após cancelamento ou resposta obsoleta.

O cliente tipado conhece os filtros públicos para evolução posterior, mas esta
primeira tela não oferece controles de filtro. Os componentes de paginação
permanecem locais, pois as features atuais possuem contratos e textos distintos;
uma extração compartilhada não trouxe benefício suficiente neste marco.
# Fundação frontend do MVP

O frontend inicial do Supervisor AI usa React, TypeScript strict, Vite e React
Router. Sua responsabilidade é adaptar a API MVP v1 para uma interface
operacional; ele não acessa sistemas externos, banco ou regras diretamente.

## Organização

A estrutura é orientada por feature:

- `app/` monta layout e rotas;
- `components/` contém layout e estados de feedback;
- `features/processing-health/` concentra a visão operacional;
- `features/financial-summary/` concentra tipos, acesso à API, hook,
  componentes e página do resumo financeiro;
- `features/commercial-events/` concentra o contrato, consulta, paginação e
  tabela dos eventos persistidos;
- `features/financial-timeline/` concentra busca por colaborador, consulta do
  Ledger e paginação;
- `lib/http/` possui o cliente fetch independente de React;
- `lib/config/` concentra ambiente;
- `styles/` define a base visual responsiva.

A raiz redireciona para `/processing-health`. Rotas desconhecidas exibem
fallback visual. O resumo financeiro está disponível em `/financial-summary`;
eventos comerciais estão disponíveis em `/commercial-events`; execuções e
timeline financeira está disponível em `/financial-timeline`; execuções
permanecem como navegação futura desabilitada.

## Integração HTTP

`VITE_API_BASE_URL` é lida em um único módulo. No desenvolvimento, `/api` passa
pelo proxy do Vite para `VITE_DEV_API_TARGET`, por padrão
`http://127.0.0.1:8000`. Essa decisão evita alterar CORS no backend enquanto
frontend e API são executados pelo fluxo local documentado.

O cliente HTTP:

- compõe URLs;
- aceita `AbortSignal`;
- interpreta JSON;
- reconhece o envelope `{error: {code, message}}`;
- diferencia erro conhecido, rede, cancelamento e resposta inválida;
- devolve somente mensagens seguras;
- não conhece React, autenticação, retry ou cache.

Cada feature valida em runtime seu contrato (`GET /processing/health`,
`GET /financial/summary` ou `GET /commercial-events`) e o representa com tipos
explícitos. A timeline valida
`GET /collaborators/{collaborator_id}/financial-timeline` da mesma forma.
Validadores
estruturais pequenos são compartilhados em `lib/http/`, sem transformar o
cliente em uma camada de domínio. Os hooks locais usam `AbortController`, tratam
loading, sucesso, erro e refetch e cancelam a chamada ao desmontar.

## Primeira tela

A página exibe exclusivamente fatos presentes no contrato:

- total de execuções;
- eventos considerados;
- eventos com e sem Ledger;
- eventos com várias execuções;
- distribuições por status e versão;
- filtros devolvidos pela API.

Não são calculados score, taxa de sucesso, tendência, duração ou diagnóstico.
Banco vazio permanece um sucesso com métricas zeradas. Falhas apresentam
mensagem segura e botão de nova tentativa.

## Resumo financeiro

A segunda tela projeta exclusivamente o contrato financeiro persistido:

- quantidade de colaboradores;
- quantidade de créditos;
- totais separados por moeda;
- colaboradores e seus valores por moeda;
- filtros devolvidos pela API.

Dinheiro permanece string decimal do transporte até a renderização. A tela não
soma moedas, não converte valores nem calcula ranking, percentual,
produtividade ou tendência. Posições e participações calculadas pelo backend
são apenas projetadas.

## Eventos comerciais

A terceira tela lista somente os seis campos públicos retornados por
`GET /commercial-events`. Não reconstrói evento, não consulta Ledger e não
deriva status ou métricas.

O cursor permanece opaco. O hook guarda uma pilha local dos cursores já
percorridos: avançar usa `next_cursor`; voltar remove a posição atual e repete a
consulta com o cursor anterior; retry repete a posição solicitada. Os dados da
página anterior são removidos durante a transição para não parecerem atuais. O
histórico desaparece ao desmontar a tela e não usa `localStorage`.

A API ordena os itens por `occurred_at` e `event_id` decrescentes. O frontend
preserva essa ordem e mostra “Página N desta sessão”, sem sugerir quantidade
total ou página absoluta.

## Timeline financeira

A rota `/financial-timeline` não consulta automaticamente. O formulário mantém
separados o texto editável e o identificador submetido; aplica apenas `trim`
externo e preserva caixa.

O hook controla estados não consultado, loading, sucesso, vazio e erro. A API
atual não distingue existência cadastral: um identificador válido sem
lançamentos retorna HTTP 200 e `items=[]`; portanto, ausência de registros é
sucesso e o frontend não infere que o colaborador existe ou não. Enquanto não
houver código público específico, qualquer erro HTTP, inclusive 404, usa o
tratamento genérico.

Ao trocar de colaborador, dados e histórico são descartados e a nova consulta
começa na página 1. Cada efeito possui `AbortController` e marcador de ciclo
ativo. Mesmo que o transporte ignore aborto, uma resposta antiga não atualiza o
estado de uma consulta mais recente.

A paginação guarda cursores opacos em uma pilha local. Retry conserva
colaborador e cursor solicitados; uma falha ao avançar permite retry ou retorno
à página anterior. A tabela preserva a ordem da API, strings decimais e
timestamps, sem saldo, totalizadores, agrupamentos ou regras.

HTML semântico, foco visível, navegação por teclado, regiões anunciáveis e
contraste constituem a base mínima de acessibilidade.

## Limites

Não há autenticação, upload, detalhes dos eventos, seleção de colaboradores,
filtros editáveis, demais
telas financeiras, gráficos avançados, estado global, polling ou deploy. Esses
recursos devem evoluir como novas features sem acoplar componentes diretamente
ao transporte HTTP.
