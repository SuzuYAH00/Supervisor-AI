# Levantamento de Processo — Relatório de Cancelamentos

## Contexto

O relatório de cancelamentos tem como objetivo identificar padrões de clientes que cancelam a conexão nos primeiros meses de contrato, buscando compreender causas recorrentes, falhas no processo e oportunidades de melhoria operacional.

Atualmente o processo é realizado manualmente, envolvendo coleta de dados, análise individual dos clientes e consolidação das informações em um relatório para apresentação à gerência.

---

# Processo Atual

## Etapa 1 — Coleta dos clientes cancelados

### Objetivo

Obter a base de clientes que cancelaram dentro do período de análise.

### Fluxo atual

1. Acessar o relatório de clientes cancelados no MK Solutions.
2. Aplicar filtro de período.
3. Aplicar filtro de motivos de cancelamento.
4. Gerar planilha com os clientes.
5. Importar dados para uma planilha central no Google Sheets.
6. Atualizar a base histórica de cancelamentos.
7. Acessar o dashboard no Looker Studio.
8. Aplicar filtros:
   - período analisado;
   - clientes com menos de 4 meses de contrato.
9. Organizar clientes por menor tempo de vida da conexão.

### Dificuldades identificadas

- Processo possui diversas etapas manuais.
- Necessidade de repetir filtros em sistemas diferentes.
- Dependência de exportação e importação de planilhas.
- Possibilidade de erros durante a manipulação dos dados.

### Tempo estimado

Aproximadamente 30 minutos.

### Potencial de melhoria

Alto.

Possíveis melhorias:
- Automatizar coleta dos dados.
- Atualizar base automaticamente.
- Centralizar informações em uma única visualização.

---

# Etapa 2 — Análise individual dos clientes

### Objetivo

Identificar características e padrões que possam explicar o cancelamento.

### Fluxo atual

Para cada cliente analisado são verificadas as seguintes informações:

- padrão da residência;
- possibilidade de imóvel alugado;
- realização do pós-instalação;
- tempo entre instalação e pós-instalação;
- histórico de atendimentos;
- resumo dos contatos realizados;
- pagamentos realizados antes do cancelamento;
- pendências financeiras;
- visitas técnicas realizadas;
- motivo real identificado para o cancelamento;
- comparação entre motivo identificado e motivo registrado no MK;
- vendedor responsável pela venda.

### Dificuldades identificadas

- Grande quantidade de informações espalhadas.
- Necessidade de acessar diversos registros manualmente.
- Alto volume de leitura e interpretação.
- Processo depende de análise individual.

### Tempo estimado

Até 10 horas, distribuídas em alguns dias.

### Potencial de melhoria

Muito alto.

Possíveis melhorias:
- Consolidação automática das informações do cliente.
- Geração de resumo dos atendimentos.
- Apoio da IA na identificação de padrões.
- Sugestão de categorias de causas.

Observação:
A análise final e validação dos motivos devem permanecer sob responsabilidade humana.

---

# Etapa 3 — Construção do relatório final

### Objetivo

Transformar os dados analisados em informações estratégicas para a gerência.

### Fluxo atual

- Analisar dados do dashboard.
- Identificar padrões recorrentes.
- Avaliar indicadores relacionados.
- Registrar problemas encontrados.
- Criar possíveis soluções.
- Estruturar documento para apresentação.

### Dificuldades identificadas

- Consolidação manual das informações.
- Necessidade de organizar diversos dados antes da apresentação.
- Tempo elevado para transformar análise em documento.

### Tempo estimado

Até 4 horas.

### Potencial de melhoria

Alto.

Possíveis melhorias:
- Geração automática de rascunho do relatório.
- Organização dos padrões encontrados.
- Apoio da IA na criação de insights.

---

# Resumo do processo

Tempo total estimado:

- Coleta: 30 minutos.
- Análise individual: até 10 horas.
- Relatório final: até 4 horas.

Tempo aproximado total:

14 horas e 30 minutos.

---

# Observação para o Supervisor AI

Este processo representa uma oportunidade de automação devido ao alto volume de atividades manuais, necessidade de consolidação de informações e possibilidade de utilização de IA para análise e geração de relatórios.
