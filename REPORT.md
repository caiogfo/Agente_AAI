# Relatório do Desafio — AI Financial Advisor (Enter / XP)

*Caio Gomes · case técnico Enter. Resumo de 2 páginas: o que estava errado na v1, como
resolvi e o que faria com mais tempo.*

---

## 1. Os principais problemas da primeira versão

A v1 não estava só "feia". Ela quebrava na execução e, pior, entregava números sem
lastro ao cliente. Foi isso que mais me preocupou. Abaixo o que encontrei.

| # | Problema | Evidência | Impacto |
|---|---|---|---|
| 1 | Caminhos fixos de Windows | `C:\Users\blope\Downloads\...` nos nós Text | O grafo não roda em outra máquina |
| 2 | Rentabilidade inventada | CSV de preços nunca conectado; a carta cita "3,5%" sem base | Número sem lastro enviado ao cliente |
| 3 | Macro alucinado | Carta dizia Selic ~9%, "Fed corta em julho", câmbio 4,70 | A fonte XP diz Selic 15,50%, câmbio 6,20, sem corte do Fed |
| 4 | Cliente errado | Carta endereçada a "João"; o cliente é Albert | Falha grosseira de personalização |
| 5 | Sem lógica de compra e venda | Recomendações genéricas | Não cumpre o objetivo do case |
| 6 | Sem formatação | Texto cru do modelo | Longe de "pronto para enviar" |
| 7 | Horizontes misturados | Retorno desde a compra tratado como mensal | HAPV3 é -74,6% desde a compra, mas +76,4% só no mês |
| 8 | Tudo a cargo do modelo (temp 0,5) | Nenhum cálculo determinístico | Alucinação numérica estrutural |

## 2. A abordagem, e por que decidi assim

A decisão que organiza todo o resto foi separar o cálculo da narração. Um motor em
Python, determinístico e coberto por testes, calcula cada número e grava um `facts.json`.
O modelo de linguagem apenas escreve a carta a partir desses fatos. Ele nunca cria um
valor. Foi assim que matei pela raiz a alucinação que contaminava a v1.

Sobre o perfil, tratei Albert como um investidor conservador. A prioridade passa a ser
preservar capital e reduzir a exposição à volatilidade, com a renda fixa e os fundos
pós-fixados no centro da carteira. A alocação-alvo documentada reflete isso: 10% em
ações, 30% em fundos e 60% em renda fixa.

Combinei as três frentes sugeridas pelo case.

Na **rentabilidade**, apuro o retorno mensal das ações pelos preços do extrato e o da
renda fixa pelo IPCA real do mês somado ao spread contratual. Os fundos são estimados
pela referência de mercado de cada estratégia, CDI para os pós-fixados e multimercado,
Ibovespa para os de ações. O resultado do mês ficou em torno de +2,58%, acima do CDI.
Mais importante para um perfil conservador, trouxe a leitura acumulada desde os aportes,
que está em -2,03%. As ações puxam para baixo (-38,7%), enquanto a renda fixa (+34,9%) e
os fundos (+11,2%) seguram o patrimônio. Esse contraste é o que sustenta a tese de
reposicionamento.

Nos **dados externos**, uso o BCB para CDI e IPCA do mês e o Yahoo Finance para Ibovespa
(+3,69%) e S&P 500 (-0,76%) de abril de 2025. Tudo com cache e fallback, então o pipeline
roda mesmo offline.

Na **lógica de compra e venda**, o motor é baseado em regras e explicável. Ele recomenda
alocar o caixa ocioso, reduzir os fundos de maior volatilidade, rebalancear em direção à
renda fixa, aparar a concentração em LREN3 e sair da posição frágil em HAPV3, usando a
alta do mês como janela. Cada ação carrega o número que a disparou. Para dimensionar o
ponto principal, o caixa de R$ 74.672,62 parado deixa de render cerca de R$ 791,53 por mês
ao CDI do mês (perto de R$ 10 mil ao ano), o que torna concreta a urgência de colocá-lo
para trabalhar.

Na **formatação**, a carta sai em PDF de duas páginas, com o logo da XP no cabeçalho,
data de emissão, indicadores, gráficos e cartões de recomendação, gerada por código e
modular por assessor e por cliente, pronta para escalar. A data segue a linha do tempo do
case (12 de maio de 2025, poucos dias após o extrato de 07/05), e não o relógio da máquina,
para a carta nunca sair com um ano anacrônico. Para a leitura ficar limpa, nomes longos de
fundo são encurtados por uma regra genérica (sem de-para por ativo, então escala) e a narração
agrupa os fundos por estratégia em vez de listar todos.

Sobre **escala**, o pipeline já roda uma base inteira. Cada cliente é um JSON em `data/` com
seu próprio cliente e assessor, e `python -m engine.run --all` gera uma carta por cliente. As
análises se adaptam ao perfil de cada um: a política de alocação-alvo e os guardrails saem do
`risk_profile` (Conservador, Moderado ou Agressivo), então recomendações e texto mudam por
cliente, não só os números. Para comprovar, incluí um segundo cliente (Beatriz Almeida,
Moderado, outra assessora): o lote produz as duas cartas, cada uma com seu plano.

Sobre **ingestão automática**, fechei a última etapa manual: o `engine/ingest.py` lê o texto
do extrato e usa o modelo para estruturá-lo em JSON, mas mantém o princípio anti-alucinação
mesmo aqui. O modelo propõe a estrutura e uma camada determinística de reconciliação confere,
até o centavo, que as partes amarram nos próprios totais do extrato (soma das posições igual ao
total investido, investido mais caixa igual ao patrimônio, o percentual de cada posição igual à
sua fatia do investido). Se algo não bate, o registro é rejeitado para revisão, nunca aceito em
silêncio. Validei contra o extrato real do Albert, que reconcilia e reproduz a transcrição feita
à mão.

A garantia de qualidade vem de 42 testes em pytest, com a aritmética conferida à mão até
o centavo. Há testes que travam regressões clássicas, como o nome do cliente, a coerência
do macro com a fonte, a ausência de caminhos de Windows no grafo e a reconciliação da ingestão
(o extrato correto passa, qualquer número adulterado é rejeitado).

## 3. O que eu faria com um mês inteiro

O passo mais valioso seria buscar a cota diária real de cada fundo na base da CVM e
casá-la por CNPJ, eliminando a única estimativa que ainda existe no retorno total. Na
ingestão, evoluiria do texto já extraído para o PDF nativo com OCR e validaria mais formatos de
extrato (cada banco tem o seu), sempre com a mesma reconciliação como rede de segurança.

Montaria também um harness de avaliação com captura de feedback do assessor. Toda carta
passaria por checagens automáticas, como verificar se cada número existe no `facts.json`,
medir o tom e o tamanho, antes de seguir para o envio. Esse é o caminho honesto para o
"aprendizado contínuo": ajustar prompts e regras com base em sinais reais, não prometer
re-treino de modelo. Por fim, acrescentaria projeções de cenários para o patrimônio,
sempre rotuladas como premissas, e testes A/B de NPS por estilo de carta.

---
*Stack: Python (pandas, matplotlib, reportlab), BCB e Yahoo Finance, Anthropic Claude no
Rivet. Como rodar: `python -m engine.run` (ver `README.md`).*
