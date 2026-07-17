# Especificação funcional — Upgrades e remuneração

## 1. Objetivo do módulo

Definir como identificar, classificar, acompanhar e remunerar eventos comerciais
relacionados a alterações de plano, Mesh e adicionais vendidos por colaboradores
do suporte.

O módulo deve produzir uma visão auditável desde o evento comercial até seu
crédito ou débito na carteira do colaborador, sem confundir execução
administrativa, autoria da venda, pagamento do cliente e pagamento da
remuneração.

## 2. Escopo

Estão no escopo:

- identificação de alterações contratuais e eventos comerciais;
- classificação independente de alteração de plano, upgrade, downgrade e
  adicional;
- renovação de fidelidade;
- elegibilidade do colaborador;
- autoria da venda por ticket;
- detecção de possível duplicidade de autoria;
- validação pela primeira fatura que contenha o novo valor ou produto;
- expiração do prazo de validação;
- acompanhamento de cancelamentos de adicionais;
- créditos e penalidades na carteira do colaborador;
- rastreabilidade dos eventos, faturas e lançamentos.

Não estão definidos neste documento:

- cálculo de RV, CSAT ou outros indicadores;
- valores de adicionais que não foram informados;
- resolução automática de disputas de autoria;
- regras contábeis, tributárias ou de folha de pagamento;
- forma de integração com sistemas operacionais;
- decisões técnicas de armazenamento ou implementação.

## 3. Conceitos de negócio

### Plano

Um plano é identificado principalmente pela velocidade e pela modalidade
comercial. Planos padrão e promocionais com a mesma velocidade são planos
distintos.

| Velocidade | Modalidade | Mensalidade |
|---|---|---:|
| 500 Mbps | Padrão | R$ 89,90 |
| 1000 Mbps | Padrão | R$ 99,90 |
| 1500 Mbps | Padrão | R$ 119,90 |
| 500 Mbps | Promocional | R$ 79,90 |
| 1000 Mbps | Promocional | R$ 89,90 |
| 1500 Mbps | Promocional | R$ 109,90 |

### Alteração contratual

É qualquer mudança registrada no contrato, inclusive operações administrativas,
correções, mudanças de plano, inclusões ou remoções de serviços. Uma alteração
contratual não é necessariamente um evento comercial remunerável.

### Evento comercial

É uma ocorrência individual de venda ou upgrade que pode seguir para avaliação
de remuneração. Cada evento conserva sua própria autoria, ticket, data,
classificação, validação por fatura e lançamento financeiro.

### Alteração de plano

É a mudança de velocidade, modalidade comercial ou situação do Mesh. Toda
alteração de plano renova fidelidade.

### Upgrade

É o evento cujo valor mensal final é maior que o valor mensal inicial. A
classificação por valor é independente da existência de alteração de plano.

### Downgrade

É a redução do plano, a remoção de serviço ou a redução do valor recorrente. Um
downgrade não gera crédito ao colaborador.

### Adicional comum

É um produto que não altera o plano, como IP Público, Watch TV, Câmeras e outros
produtos equivalentes. Sua inclusão pode gerar upgrade por aumento de valor; sua
remoção é downgrade.

### Mesh

É uma exceção comercial: embora seja equipamento ou adicional físico, é tratado
como plano para alteração contratual, fidelidade e remuneração.

### Crédito, débito e saldo

- Crédito é um lançamento positivo por evento comercial validado.
- Débito é um lançamento negativo, como penalidade por cancelamento precoce.
- Saldo é o resultado derivado da soma dos créditos menos a soma dos débitos.

## 4. Dados mínimos necessários

### Identificação do evento

- cliente;
- contrato;
- data do evento comercial;
- plano inicial e plano final;
- velocidade e modalidade inicial e final;
- presença de Mesh antes e depois;
- adicionais antes e depois;
- valor mensal inicial e final;
- valor recorrente de cada adicional incluído ou removido.

### Autoria e elegibilidade

- ticket;
- data de abertura do ticket;
- operador que abriu o ticket;
- área do operador na abertura;
- operador administrativo que executou a alteração;
- histórico necessário para revisão de autoria;
- vínculo entre ticket e alteração contratual.

### Validação financeira

- primeira fatura que contém o novo valor ou produto;
- vencimento da fatura;
- situação e data de pagamento;
- itens ou composição recorrente presentes na fatura;
- vínculo entre fatura e cada evento validado;
- prazo final de 35 dias após o vencimento.

### Cancelamento e monitoramento

- adicional vendido;
- data da venda;
- data de remoção, quando houver;
- primeira fatura que contém o adicional;
- data do pagamento que liberou o crédito;
- término do período de três meses;
- vínculo entre penalidade e crédito original.

### Carteira

- colaborador;
- cliente;
- contrato;
- ticket;
- evento comercial de origem;
- tipo, valor, data, justificativa e estado do lançamento;
- fatura relacionada, quando aplicável;
- vínculo com lançamento original, quando aplicável.

## 5. Regras de alteração de plano

Existe alteração de plano quando ocorrer pelo menos uma destas situações:

- mudança de velocidade;
- mudança entre plano padrão e promocional;
- adesão ao Mesh;
- remoção do Mesh.

Toda alteração de plano renova fidelidade.

Uma operação que mantenha exatamente velocidade, modalidade e situação do Mesh
não é alteração de plano. Se também não incluir adicional, não constitui
operação comercial válida.

Alteração de plano e upgrade são classificações independentes. Uma alteração de
plano pode reduzir o valor e, portanto, não ser upgrade.

## 6. Regras de upgrade

Há upgrade quando:

```text
valor mensal final > valor mensal inicial
```

O aumento pode decorrer de:

- aumento de velocidade;
- mudança de plano promocional para padrão;
- adesão ao Mesh;
- inclusão de adicional;
- mudança de plano combinada com adicional.

Quando houver simultaneamente alteração de plano, renovação de fidelidade e
upgrade elegível, o crédito corresponde ao valor integral da nova mensalidade,
após a validação da primeira fatura.

Quando não houver alteração de plano, mas houver inclusão elegível de adicional,
o crédito corresponde somente ao valor recorrente adicionado.

## 7. Regras de downgrade

Há downgrade quando ocorrer:

- redução de velocidade;
- redução do plano;
- remoção de serviço;
- redução do valor recorrente.

Downgrade não gera crédito ao colaborador.

A redução de velocidade deve permanecer registrada como downgrade mesmo quando
a inclusão simultânea de adicionais fizer o valor final superar o valor inicial.

Casos confirmados:

- 1000 Mbps para 500 Mbps: alteração de plano, fidelidade renovada e downgrade;
- remoção de adicional comum: downgrade sem alteração de plano ou fidelidade;
- remoção de Mesh: downgrade com alteração de plano e fidelidade renovada.

A operação de downgrade de plano não é permitida antes de três meses após um
upgrade de plano. O cliente deve pagar a primeira, a segunda e a terceira fatura
antes de poder realizar o downgrade. Essa restrição não posterga o crédito do
upgrade, liberado após a primeira fatura paga.

## 8. Regras de adicionais

São adicionais comuns:

- IP Público;
- Watch TV;
- Câmeras;
- outros produtos que não alterem o plano.

A inclusão de adicional comum:

- não é alteração de plano;
- não renova fidelidade;
- é upgrade se elevar o valor mensal;
- quando elegível, paga apenas o valor do adicional ou a diferença recorrente.

A remoção de adicional comum:

- é downgrade;
- não é alteração de plano;
- não renova fidelidade;
- não gera crédito.

Cada inclusão deve ser registrada como evento separado, inclusive quando uma
mesma fatura validar mais de uma venda.

## 9. Regra especial do Mesh

O Mesh é tratado como plano.

Exemplos confirmados:

| Plano sem Mesh | Plano com Mesh |
|---|---:|
| 500 Mbps padrão — R$ 89,90 | 500 Mbps Mesh — R$ 109,90 |
| 1000 Mbps padrão — R$ 99,90 | 1000 Mbps Mesh — R$ 119,90 |
| 1500 Mbps padrão — R$ 119,90 | 1500 Mbps Mesh — R$ 139,90 |

A adesão ao Mesh:

- é alteração de plano;
- renova fidelidade;
- é upgrade se o valor final aumentar;
- quando elegível e validada, gera crédito integral da nova mensalidade.

A remoção do Mesh:

- é alteração de plano;
- renova fidelidade;
- é downgrade;
- não gera crédito.

## 10. Regras de fidelidade

Toda alteração de plano renova fidelidade. Isso inclui:

- mudança de velocidade;
- mudança entre padrão e promocional;
- adesão ao Mesh;
- remoção do Mesh.

Inclusão ou remoção de adicional comum não renova fidelidade.

Fidelidade e upgrade são conclusões independentes. Renovar fidelidade não basta
para gerar remuneração: também deve existir evento elegível e pagamento válido.

## 11. Elegibilidade do colaborador

Uma alteração entra no fluxo de remuneração somente quando todas as condições
forem atendidas:

1. existe um ticket relacionado;
2. o ticket foi aberto por colaborador do suporte;
3. a alteração representa venda ou upgrade elegível;
4. o cliente pagou a primeira fatura que contém o novo valor ou produto dentro
   do prazo máximo.

Atualmente, somente colaboradores do suporte recebem premiação por upgrades.

Não geram remuneração:

- alterações administrativas;
- correções contratuais;
- alterações sem ticket do suporte;
- tickets abertos por pessoas fora do suporte;
- downgrades;
- eventos não pagos no prazo.

## 12. Identificação da autoria da venda

O operador que executa tecnicamente a alteração no sistema não é necessariamente
o autor da venda.

A autoria é identificada principalmente pelo colaborador do suporte que abriu o
ticket. O ticket deve permanecer vinculado ao evento, ao cliente, ao contrato e
ao lançamento da carteira.

Quando houver disputa ou múltiplos tickets, a autoria não pode ser concluída
somente pelo executor administrativo nem escolhida automaticamente.

## 13. Duplicidades e revisão manual

Mais de um ticket para o mesmo cliente e a mesma alteração, aberto por pessoas
diferentes, é uma possível duplicidade de autoria.

Nessa situação:

- nenhum recebedor é escolhido automaticamente;
- o evento fica pendente de revisão manual;
- o responsável consulta o histórico de contato com o cliente;
- somente quem efetivamente realizou a venda recebe;
- não pode haver dois créditos para o mesmo evento comercial.

Exemplo confirmado:

- cliente 33456;
- mudança de 1500 Mbps para 1500 Mbps + Mesh;
- ticket 2607.2656 aberto por Melissa;
- ticket 2607.2689 aberto por Luana.

O caso deve permanecer em revisão até a autoria efetiva ser confirmada.

## 14. Validação por pagamento da fatura

O crédito somente é liberado após o pagamento da primeira fatura que contenha o
novo valor ou produto.

A validação deve comprovar que o item ou valor associado ao evento está presente
na fatura paga. A existência de pagamento anterior à primeira fatura com o novo
valor não valida o evento.

Cada evento mantém vínculo próprio com a fatura que o validou.

## 15. Prazo máximo para pagamento

O pagamento deve ocorrer em até 35 dias após o vencimento da primeira fatura que
contém o novo valor ou produto.

Se não houver pagamento dentro do prazo:

- o evento expira;
- não gera remuneração;
- deixa de ser acompanhado para fins de liberação do crédito.

Exemplo:

- alteração em 10/06, de 500 Mbps para 1000 Mbps;
- fatura de 10/06 ainda em R$ 89,90;
- primeira fatura com novo valor em 10/07, no valor de R$ 99,90;
- prazo final: 35 dias após o vencimento de 10/07.

## 16. Múltiplas vendas validadas pela mesma fatura

Uma fatura pode validar vários eventos comerciais quando contiver os respectivos
valores ou produtos.

Exemplo:

- 01/08: 1000 Mbps para 1500 Mbps;
- 03/08: inclusão de IP Público;
- 10/09: pagamento de fatura contendo 1500 Mbps + IP Público.

Resultado:

- o upgrade de plano pode gerar seu crédito;
- a venda do IP pode gerar seu crédito;
- ambos vinculam-se à mesma fatura;
- os eventos continuam separados;
- a fatura não pode validar duas vezes o mesmo evento.

Essa regra existe porque a fatura comprova o pagamento de uma composição que
pode resultar de várias vendas sucessivas, sem transformar essas vendas em um
único evento.

## 17. Cancelamento de adicionais

### Antes da primeira fatura que contém o adicional

Se o adicional for removido antes de aparecer na primeira fatura:

- a venda do adicional não gera crédito;
- outros eventos válidos do mesmo contrato continuam independentes.

### Depois do pagamento da primeira fatura

Se o cliente pagar a primeira fatura contendo o adicional, o crédito é liberado.
Depois disso, o adicional permanece em monitoramento até completar três meses
desde a data da venda.

## 18. Penalidade por cancelamento precoce

Se um adicional já creditado for removido antes de completar três meses desde a
data da venda:

- é criado um lançamento negativo;
- o débito é igual a duas vezes o crédito original da venda;
- a penalidade fica vinculada ao crédito original.

Exemplo:

- venda do IP: R$ 20,00;
- crédito inicial: + R$ 20,00;
- cancelamento antes de três meses: - R$ 40,00;
- resultado líquido desses lançamentos: - R$ 20,00.

O prazo é contado desde a venda, não desde o pagamento da fatura.

## 19. Carteira do colaborador

A carteira é um extrato auditável de lançamentos positivos e negativos.

Créditos possíveis:

- upgrades de plano validados;
- adicionais validados;
- vendas de Mesh validadas.

Débitos possíveis:

- penalidades por cancelamento de adicionais dentro dos três meses;
- outros débitos somente quando forem futuramente definidos.

O saldo deve ser sempre derivado dos lançamentos:

```text
saldo = soma dos créditos - soma dos débitos
```

O saldo não é uma verdade independente dos lançamentos.

Cada lançamento registra, no mínimo:

- colaborador, cliente e contrato;
- ticket e evento comercial de origem;
- tipo, valor, data, justificativa e estado;
- fatura relacionada, quando aplicável;
- vínculo com o crédito original, quando for penalidade.

## 20. Estados do ciclo de vida de uma venda

| Estado | Significado funcional |
|---|---|
| Identificado | Evento comercial encontrado e ainda não concluído quanto à elegibilidade. |
| Não elegível | Evento que não atende às condições de remuneração. |
| Aguardando pagamento | Evento elegível aguardando a primeira fatura válida paga. |
| Pendente de revisão manual | Autoria ou consistência exige decisão humana. |
| Validado para pagamento | Fatura válida foi paga dentro do prazo e o crédito pode ser lançado. |
| Pago | Remuneração ao colaborador foi efetivada. |
| Expirado | Primeira fatura válida não foi paga no prazo máximo. |
| Adicional em monitoramento | Adicional creditado ainda não completou três meses desde a venda. |
| Encerrado | Evento concluiu seu ciclo sem pendências de pagamento ou monitoramento. |
| Penalidade gerada | Cancelamento precoce produziu débito vinculado ao crédito original. |
| Inconsistente | Dados impedem classificação ou rastreabilidade segura. |

As transições completas e os responsáveis por cada mudança de estado permanecem
em aberto na seção de pontos pendentes.

## 21. Tabela consolidada de cenários

Premissas da tabela, salvo quando o cenário disser o contrário:

- existe ticket aberto pelo suporte;
- autoria não está duplicada;
- a primeira fatura aplicável foi paga dentro do prazo;
- “pagamento integral” significa a nova mensalidade recorrente completa;
- “pagamento do adicional” significa somente o valor recorrente incluído.

Legenda: **Sim**, **Não** e **Pendente** quando os dados confirmados não permitem
uma resposta booleana sem nova decisão de negócio.

| Cenário | Alteração de plano | Renova fidelidade | Upgrade | Downgrade | Adicional comum | Elegível para pagamento | Tipo de pagamento | Exige monitoramento | Exige revisão manual |
|---|---|---|---|---|---|---|---|---|---|
| 500 para 1000 Mbps | Sim | Sim | Sim | Não | Não | Sim | Mensalidade integral nova | Não | Não |
| 1000 para 500 Mbps | Sim | Sim | Não | Sim | Não | Não | Nenhum | Não | Não |
| 1000 para 1000 + IP | Não | Não | Sim | Não | Sim | Sim | Valor do IP | Sim | Não |
| 1000 para 1000 + Watch | Não | Não | Sim | Não | Sim | Sim | Valor do Watch | Sim | Não |
| 1000 para 1000 + Câmeras | Não | Não | Sim | Não | Sim | Sim | Valor das Câmeras | Sim | Não |
| 1000 para 1000 + Mesh | Sim | Sim | Sim | Não | Não | Sim | Mensalidade integral nova | Não | Não |
| 1000 para 1500 + IP | Sim | Sim | Sim | Não | Sim | Sim | Mensalidade integral nova | Pendente | Não |
| 1500 para 1000 + IP | Sim | Sim | Pendente, se total final maior | Sim | Sim | Não | Nenhum | Não | Não |
| Padrão para promocional | Sim | Sim | Não | Sim | Não | Não | Nenhum | Não | Não |
| Padrão para promocional + IP | Sim | Sim | Sim, se total final maior | Não | Sim | Sim, se total final maior | Mensalidade integral nova | Pendente | Não |
| Promocional para padrão | Sim | Sim | Sim | Não | Não | Sim | Mensalidade integral nova | Não | Não |
| Remoção de IP | Não | Não | Não | Sim | Sim | Não | Nenhum | Não | Não |
| Remoção de Watch | Não | Não | Não | Sim | Sim | Não | Nenhum | Não | Não |
| Remoção de Câmeras | Não | Não | Não | Sim | Sim | Não | Nenhum | Não | Não |
| Remoção de Mesh | Sim | Sim | Não | Sim | Não | Não | Nenhum | Não | Não |
| Alteração administrativa sem ticket | Conforme alteração | Conforme alteração | Conforme valores | Conforme alteração | Conforme itens | Não | Nenhum | Não | Não |
| Ticket aberto fora do suporte | Conforme alteração | Conforme alteração | Conforme valores | Conforme alteração | Conforme itens | Não | Nenhum | Não | Não |
| Duplicidade de autoria | Conforme alteração | Conforme alteração | Conforme valores | Conforme alteração | Conforme itens | Pendente | Pendente | Conforme adicional | Sim |
| Adicional removido antes da primeira fatura | Não | Não | Sim no evento original | Sim na remoção | Sim | Não | Nenhum | Não | Não |
| Adicional removido depois da primeira fatura, dentro de três meses | Não | Não | Sim no evento original | Sim na remoção | Sim | Sim para o crédito original | Crédito do adicional e débito de 2× | Sim | Não |
| Adicional mantido por mais de três meses | Não | Não | Sim | Não | Sim | Sim | Valor do adicional | Sim até completar três meses | Não |

## 22. Exemplos completos

### Exemplo A — Upgrade de plano

Um colaborador do suporte abre ticket para alterar um cliente de 500 Mbps padrão
(R$ 89,90) para 1000 Mbps padrão (R$ 99,90). O administrativo executa a mudança.
A primeira fatura com R$ 99,90 é paga dentro do prazo.

Resultado:

- alteração de plano: sim;
- renovação de fidelidade: sim;
- upgrade: sim;
- autor: colaborador do suporte que abriu o ticket;
- executor administrativo: não recebe por esse fato;
- crédito: R$ 99,90;
- fatura paga vinculada ao evento.

### Exemplo B — Alteração sem upgrade

Cliente muda de 1000 Mbps padrão (R$ 99,90) para 1000 Mbps promocional
(R$ 89,90).

Resultado:

- alteração de plano: sim;
- renovação de fidelidade: sim;
- upgrade: não;
- downgrade por redução recorrente: sim;
- crédito: nenhum.

### Exemplo C — Alteração de modalidade combinada com IP

Cliente muda de 1000 Mbps padrão (R$ 99,90) para 1000 Mbps promocional + IP
Público, com total final de R$ 109,90. Existe ticket elegível e a primeira fatura
é paga no prazo.

Resultado:

- alteração de plano: sim;
- renovação de fidelidade: sim;
- upgrade: sim;
- crédito: valor integral da nova mensalidade, R$ 109,90;
- o evento preserva o adicional incluído e a fatura que validou o total.

### Exemplo D — Duas vendas validadas por uma fatura

- 01/08: colaborador A vende mudança de 1000 para 1500 Mbps;
- 03/08: colaborador B vende IP Público;
- 10/09: cliente paga fatura contendo 1500 Mbps + IP Público.

Resultado:

- evento A: crédito integral da nova mensalidade do upgrade de plano;
- evento B: crédito do valor do IP Público;
- a mesma fatura comprova ambos;
- cada evento e cada crédito permanecem separados;
- nenhum evento pode ser creditado novamente pela mesma fatura.

### Exemplo E — Adicional removido antes da primeira fatura

- 01/08: upgrade de 1000 para 1500 Mbps;
- 03/08: inclusão de IP Público;
- 05/08: remoção do IP Público;
- 10/09: pagamento de fatura contendo somente 1500 Mbps.

Resultado:

- o upgrade de plano é validado e creditado;
- a venda do IP não é creditada;
- a remoção do IP é registrada como downgrade sem crédito.

### Exemplo F — Penalidade por cancelamento precoce

Um adicional de R$ 20,00 é vendido e aparece na primeira fatura paga. O
colaborador recebe crédito de R$ 20,00. O adicional é removido antes de três
meses desde a venda.

Resultado na carteira:

- crédito original: + R$ 20,00;
- penalidade vinculada: - R$ 40,00;
- efeito líquido: - R$ 20,00.

### Exemplo G — Possível duplicidade

Melissa e Luana possuem tickets diferentes para a mesma adesão ao Mesh do
cliente 33456.

Resultado:

- evento pendente de revisão manual;
- nenhum crédito é atribuído automaticamente;
- histórico de contato deve ser analisado;
- somente a autora efetiva recebe.

## 23. Invariantes de negócio

1. Toda alteração de plano renova fidelidade.
2. Adicional comum não renova fidelidade.
3. Mesh é tratado como plano.
4. Alteração de plano e upgrade são classificações independentes.
5. Downgrade não gera crédito.
6. Toda remuneração exige ticket elegível aberto pelo suporte.
7. Executor administrativo não é presumido como autor da venda.
8. Toda remuneração exige primeira fatura aplicável paga dentro do prazo.
9. Um evento comercial não pode receber crédito duplicado.
10. Uma fatura pode validar vários eventos comerciais distintos.
11. Cada evento permanece individual, mesmo quando compartilha fatura.
12. Adicional removido antes da primeira fatura aplicável não gera crédito.
13. Penalidade por cancelamento precoce equivale a duas vezes o crédito original.
14. Toda penalidade fica vinculada ao crédito original.
15. O período de três meses começa na data da venda do adicional.
16. O crédito do upgrade de plano é liberado após a primeira fatura paga.
17. O downgrade de plano permanece bloqueado até o pagamento das três primeiras
    faturas posteriores ao upgrade.
18. Alteração administrativa ou correção sem ticket do suporte não gera crédito.
19. O saldo da carteira é derivado dos lançamentos.
20. Toda decisão de autoria, elegibilidade, validação e penalidade deve ser
    rastreável às evidências que a justificam.

## 24. Casos que não geram remuneração

- operação que mantém exatamente o mesmo plano, modalidade e Mesh, sem adicional;
- downgrade de plano;
- remoção de adicional comum;
- remoção de Mesh;
- alteração administrativa;
- correção contratual;
- alteração sem ticket;
- ticket não aberto pelo suporte;
- evento sem primeira fatura aplicável paga no prazo;
- adicional removido antes da primeira fatura que o contém;
- possível duplicidade ainda não resolvida;
- evento já creditado anteriormente;
- alteração que não representa venda ou upgrade elegível.

## 25. Pontos pendentes

Os itens abaixo não possuem definição suficiente nas regras confirmadas e não
devem ser decididos durante a implementação:

1. Definição exata de “fatura paga”: pagamento parcial, negociado ou compensado
   também valida o evento?
2. O prazo de 35 dias inclui o próprio dia do vencimento e termina em qual
   horário?
3. “Três meses” significa meses-calendário ou quantidade fixa de dias?
4. Como contar o período quando a data de venda não existe no mês final?
5. Quais transições de estado são permitidas e quem é responsável por cada uma?
6. Qual estado representa lançamento criado na carteira e qual representa valor
   efetivamente pago ao colaborador?
7. Como tratar estorno, cancelamento ou reversão da fatura após o crédito?
8. Como tratar pagamento realizado após a expiração de 35 dias?
9. Como determinar a primeira fatura aplicável em ciclos proporcionais, mudança
   de vencimento ou faturamento agrupado?
10. Como calcular o valor do adicional quando existem descontos, várias unidades
    ou preço proporcional?
11. Em mudança de plano combinada com adicional, o adicional também permanece em
    monitoramento e pode gerar penalidade separada, embora o crédito tenha sido a
    mensalidade integral?
12. Em redução de velocidade combinada com adicional e valor final maior, o
    aumento do total deve coexistir formalmente com a classificação de upgrade?
    A remuneração não está pendente: o downgrade de velocidade não gera crédito,
    mesmo acompanhado por adicional.
13. Como classificar padrão para promocional + adicional quando o valor final não
    for maior que o inicial?
14. A penalidade de cancelamento precoce aplica-se ao Mesh ou apenas a adicionais
    comuns?
15. A remoção parcial de várias câmeras gera penalidade proporcional por unidade?
16. Como tratar troca de adicional por outro adicional no mesmo evento?
17. Como tratar múltiplos tickets do mesmo colaborador para o mesmo evento?
18. Quais critérios temporais e de conteúdo vinculam um ticket a uma alteração?
19. Como decidir autoria em venda compartilhada, transferência ou reabertura de
    ticket?
20. A elegibilidade considera a área do colaborador na abertura do ticket, na
    alteração ou no pagamento?
21. Quem realiza a revisão manual e quais evidências mínimas devem ser registradas?
22. Qual é o fluxo quando a revisão manual não consegue determinar a autoria?
23. A carteira pode possuir saldo negativo e como esse saldo transita entre
    períodos?
24. Como tratar desligamento ou mudança de equipe durante monitoramento?
25. Como comprovar o pagamento da primeira, segunda e terceira fatura para liberar
    downgrade de plano em casos de atraso ou renegociação?
26. Os valores de planos e Mesh listados são um catálogo fixo desta regra ou
    referências vigentes que podem mudar na fonte oficial?
27. Quais produtos futuros são adicionais comuns e quais devem ter comportamento
    semelhante ao Mesh?
28. Como tratar inconsistências entre ticket, contrato, alteração e fatura?
29. Qual é o processo de correção de um lançamento incorreto já pago?
30. Quando um upgrade de plano e uma venda posterior de adicional são validados
    pela mesma fatura, qual composição exata define a “mensalidade integral” do
    crédito do upgrade de plano?
31. Se o pagamento que valida um adicional ocorrer quando já tiverem transcorrido
    três meses desde a venda, o evento ainda exige algum período de monitoramento?

## 26. Critérios de aceite da especificação

A especificação é aceita quando a equipe de negócio confirmar que:

- alteração contratual, evento comercial, alteração de plano, upgrade, downgrade
  e adicional estão diferenciados corretamente;
- planos padrão e promocionais de mesma velocidade são reconhecidos como
  distintos;
- fidelidade está separada de upgrade e remuneração;
- Mesh está tratado conforme sua exceção comercial;
- autoria da venda está separada da execução administrativa;
- elegibilidade exige ticket do suporte e primeira fatura paga;
- créditos de plano e adicionais estão diferenciados;
- prazo de 35 dias está descrito corretamente;
- múltiplos eventos podem compartilhar uma fatura sem duplicar crédito;
- cancelamento antes da primeira fatura impede crédito do adicional;
- penalidade após cancelamento precoce está vinculada ao crédito original;
- carteira diferencia crédito, débito e saldo;
- estados funcionais cobrem o ciclo esperado sem antecipar implementação;
- tabela de cenários foi validada pelos responsáveis do negócio;
- exemplos representam corretamente as regras operacionais;
- invariantes não contêm contradições;
- todos os pontos pendentes foram respondidos ou formalmente aceitos para etapa
  posterior;
- o documento não depende de tecnologia específica nem define solução técnica.
