# Qualidade / Monitoria de Atendimento

## Estado do domínio

Qualidade existiu como indicador operacional produzido por um processo humano
de auditoria. O setor responsável por esse processo foi descontinuado e deixou
de produzir novas avaliações.

Por decisão explícita de escopo, Qualidade está suspensa no MVP atual. O
Supervisor AI não terá, nesta etapa, modelo persistente, importação, cálculo,
API ou integração para esse indicador.

Essa ausência não representa falha técnica. Um mecanismo próprio de auditoria
deverá ser especificado e projetado futuramente.

## Processo histórico

Ao final de cada mês, o setor de Qualidade considerava os atendimentos
realizados por cada operador e auditava uma amostra equivalente a 5% do total de
atendimentos daquele operador.

Exemplo operacional informado:

- 100 atendimentos realizados no mês;
- 5 atendimentos auditados.

As auditorias eram humanas e podiam envolver:

- escuta de ligações;
- leitura de conversas por chat.

Cada atendimento auditado recebia uma nota individual de qualidade. A média
das notas da amostra produzia o indicador de Qualidade do colaborador naquele
processo histórico.

Depois da apuração, um relatório era enviado por e-mail. A nota ou média de
Qualidade era lançada manualmente no campo correspondente da planilha de cada
colaborador.

## Regras históricas conhecidas

As seguintes características estão confirmadas apenas para o processo antigo:

1. a população mensal era observada por operador;
2. a amostra auditada correspondia operacionalmente a 5% dos atendimentos
   totais do operador;
3. ligações e conversas por chat podiam ser auditadas;
4. cada atendimento da amostra recebia uma nota;
5. o indicador do colaborador era a média das notas dos atendimentos auditados;
6. o resultado era comunicado por relatório ou e-mail;
7. o lançamento na planilha do colaborador era manual.

Essas características são evidência e referência operacional. Elas não formam
o contrato do futuro mecanismo de auditoria do Supervisor AI.

A documentação disponível não confirma a escala histórica das notas, regras de
arredondamento, critérios avaliados, pesos, identidade técnica das monitorias ou
tratamento de frações na seleção da amostra. Esses detalhes não devem ser
reconstruídos por suposição.

## Situação atual

O setor que realizava as auditorias foi descontinuado. Consequentemente:

- o processo histórico não produz novas avaliações;
- não existe atualmente fonte operacional contínua de Qualidade;
- relatórios e planilhas antigas não serão integrados como fluxo corrente;
- o Supervisor AI não automatizará nem reproduzirá o processo descontinuado.

Eventuais registros históricos não devem ser tratados como fonte ativa sem uma
decisão específica sobre preservação, semântica e qualidade desses dados.

## Decisão para o MVP

Qualidade não será implementada como indicador operacional nesta etapa do MVP.
Não serão criados:

- entidade ou tabela de monitoria;
- migration;
- contrato de importação;
- endpoint;
- cálculo de nota ou média;
- auditoria automática;
- efeito sobre RV.

Qualidade permanece mencionada no escopo de produto como evolução futura, mas
não participa dos contratos executáveis atuais.

## Futuro módulo de auditoria

O Supervisor AI deverá futuramente possuir uma forma própria de selecionar e
auditar atendimentos e produzir fatos de Qualidade. Esse módulo precisará de
especificação operacional e arquitetural própria antes da implementação.

O processo histórico não determina que o futuro mecanismo:

- use amostra de exatamente 5%;
- preserve a fórmula histórica;
- mantenha a mesma escala de nota;
- seja totalmente automático;
- utilize IA;
- processe áudio ou chats automaticamente;
- produza impacto em RV.

Fatos de auditoria, seleção de amostra, aplicação de critérios e eventuais
cálculos deverão permanecer responsabilidades explícitas e separadas.

## Regras futuras ainda não definidas

O futuro mecanismo exige decisões sobre:

1. população de atendimentos elegível para auditoria;
2. método, período e quantidade de seleção da amostra;
3. tratamento de arredondamento e população pequena, caso exista percentual de
   amostragem;
4. canais incluídos e acesso seguro às evidências de cada atendimento;
5. critérios avaliados, pesos e possíveis critérios eliminatórios;
6. escala, precisão e regras de arredondamento das notas;
7. quantidade mínima de avaliações necessária para produzir um indicador;
8. identidade e rastreabilidade da auditoria, do atendimento e do avaliador;
9. processo manual, assistido ou automático de avaliação;
10. papel eventual de IA, áudio e conversas por chat;
11. revisão, contestação e correção de uma auditoria;
12. campos públicos e tratamento de observações ou dados sensíveis;
13. comparabilidade entre canais, formulários e períodos;
14. eventual relação com RV, que deverá ser especificada em domínio próprio.

Até que essas decisões sejam aprovadas, nenhuma regra histórica deve ser
promovida silenciosamente a regra vigente.
