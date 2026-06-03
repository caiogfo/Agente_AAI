# Relatório do Desafio — AI Financial Advisor (Enter / XP)

*Candidato · case técnico Enter. Resumo de 2 páginas: problemas do v1, abordagem e próximos passos.*

---

## 1. Os principais problemas da primeira versão

Analisando o grafo Rivet v1 e a carta `output_letter.docx`, encontrei falhas que iam de
quebra de execução a erros que comprometeriam a confiança do cliente:

| # | Problema | Evidência | Impacto |
|---|---|---|---|
| 1 | **Caminhos hardcoded Windows** | `C:\Users\blope\Downloads\...` nos nós Text | O grafo **não roda** em outra máquina |
| 2 | **Rentabilidade inventada** | CSV de preços **não conectado**; carta diz "3,5%" sem base | Número sem lastro entregue ao cliente |
| 3 | **Macro alucinado** | Carta: Selic ~9%, "Fed corta em julho", câmbio 4,70 | Fonte XP diz **15,50%**, **6,20**, sem corte do Fed |
| 4 | **Cliente errado** | "Prezado **João**" (cliente é **Albert**) | Erro grosseiro de personalização |
| 5 | **Sem lógica de compra/venda** | Recomendações genéricas | Não cumpre o objetivo do case |
| 6 | **Sem formatação** | Texto cru do LLM | Longe de "pronto para enviar" |
| 7 | **Mistura de horizontes** | Retorno *desde a compra* tratado como mensal | Ex.: HAPV3 é **−74,6% desde a compra** mas **+76,4% no mês** |
| 8 | **Tudo a cargo do LLM (temp 0,5)** | Nenhum cálculo determinístico | Alucinação numérica estrutural |

## 2. A abordagem — e por que decidi assim

**Tese central: separar CÁLCULO de NARRAÇÃO.** Um motor Python determinístico e
**testado** produz um `facts.json`; o LLM (Claude, no Rivet) apenas **narra** esses
fatos e está proibido de criar números. Isso ataca a causa-raiz dos problemas #2, #3 e #8.

Combinei as **três** áreas de melhoria sugeridas:

- **Rentabilidade (apurada vs estimada).** Calculo o retorno do mês das **ações** pelos
  preços do CSV (fonte da verdade, bate com o extrato) e da **renda fixa** pelo IPCA real
  (BCB) + spread contratual. Para os **fundos** — cuja cota mensal **não existe nos dados** —
  uso uma estimativa (proxy CDI) **explicitamente sinalizada**, em vez de inventar. Resultado:
  ações **+7,74%** (apurado), carteira **≈+2,32%** (estimativa), **+1,26 p.p. vs CDI**.
  *Por que assim:* honestidade analítica vale mais que um número bonito sem lastro — e
  expõe um gap de dados real (ver §3).
- **Dados externos (o que o case pediu).** **BCB SGS** para CDI/IPCA do mês e **Yahoo
  Finance** para **Ibovespa (+3,69%)** e **S&P 500 (−0,76%)** de abr/2025 — benchmarks reais,
  grátis, com cache e *fallback* para rodar offline.
- **Compra/venda (rule-based, explicável).** Motor dirigido pelo perfil moderado: alocar
  **R$55k de caixa ocioso** (custo de oportunidade alto com Selic 15,5%), **rebalancear**
  (fundos +17,7 p.p. acima do alvo / RF −17 p.p. abaixo), **aparar concentração** em LREN3
  (>7%), **sair de HAPV3** (impaired, sem dividendos — usando a alta de +76% no mês como
  janela), e **manter o núcleo** de LREN3 (qualidade, paga dividendos). Cada ação carrega o
  número que a disparou.
- **Formatação automatizada.** PDF de **2 páginas** com identidade visual XP (amarelo/preto),
  KPIs, gráficos e cartões de recomendação — gerado **programaticamente** (reportlab), modular
  por assessor/cliente para escalar (o objetivo "3x mais clientes").

**Garantia de qualidade:** 31 testes `pytest`, com a aritmética conferida à mão até o
centavo (margem 0% nos cálculos determinísticos) e testes que travam regressões clássicas
(nome do cliente, macro vs fonte, ausência de caminhos Windows no Rivet).

## 3. O que eu faria com um mês inteiro

1. **Cota mensal dos fundos** (o maior gap): integrar a base de cotas (CVM/XP) para apurar
   os 67,7% hoje estimados — eliminando a única estimativa do retorno total.
2. **Ingestão automática** do extrato (PDF→estruturado via OCR/LLM) para remover a transcrição
   manual e escalar para milhares de clientes.
3. **Harness de avaliação + feedback** (o "aprendizado contínuo" de forma honesta): um conjunto
   de checagens automáticas (todo número da carta existe no `facts.json`?, tom, tamanho) e
   captura do feedback do assessor para *fine-tuning* de prompt — não re-treino de modelo.
4. **Projeções de cenários** (base/otimista/pessimista) para o patrimônio, rotuladas como
   premissas, com gráfico de evolução.
5. **Personalização de voz** por assessor e **A/B testing** de NPS por estilo de carta.
6. **Orquestração em produção**: fila por carteira, geração em lote, e *guardrails* de
   compliance (CVM) automatizados antes do envio.

---
*Stack: Python (pandas, matplotlib, reportlab), BCB SGS + Yahoo Finance, Anthropic Claude
no Rivet. Rodar: `python -m engine.run` (ver `README.md`).*
