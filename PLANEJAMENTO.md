# PLANEJAMENTO — AI Financial Advisor para clientes XP (case Enter)

> Documento de planejamento e documentação completa do material do case.
> Autor da solução: Caio Gomes (case técnico Enter). Cliente tema: XP Investimentos.

---

## 1. Objetivo do case (o que o cliente realmente pediu)

Fonte: `README.md.docx`. A XP tem 20k+ assessores; cada um atende 50–300 clientes e
tem dificuldade de entregar aconselhamento de qualidade ao segmento **middle-market**
(< R$1M). O pedido é um **PoC de workflow de LLM** que permita ao assessor atender
**3x mais** clientes, gerando um **relatório mensal (carta, em português)** que explique:

1. Como a carteira do cliente performou;
2. Como eventos macro podem afetar a carteira no futuro;
3. Como ajustar a carteira de forma compatível com **(A)** o perfil de risco e
   **(B)** as recomendações da pesquisa da casa.

Já existe um **MVP v1** (grafo Rivet + `Output/output_letter.docx`) que **não atende**
ao padrão de qualidade. A tarefa é diagnosticar, iterar e elevar o nível, escolhendo ao
menos uma das áreas de melhoria — aqui **combinamos as três**: (1) cálculo de
rentabilidade, (2) lógica de compra/venda, (3) formatação automatizada.

**Restrições do case:** relatório de até 2 páginas; prompts/código/grafo em inglês;
carta final em português, em formato de carta.

---

## 2. Inventário do material (todos os arquivos)

| Arquivo | O que é | Uso na solução |
|---|---|---|
| `README.md.docx` | Briefing do case | Requisitos, restrições, entregáveis |
| `Input/XP - Albert_s portfolio.(pdf/txt)` | Extrato da carteira do Albert | Transcrito p/ `data/albert_portfolio.json` |
| `Input/XP - Albert_s risk profile.(pdf/txt)` | Perfil de risco (Moderado) | Política do motor de recomendações |
| `Input/XP - Macro analysis.(pdf/txt)` | Relatório macro XP (06/02/2025) | Fatos macro **ancorados** (anti-alucinação) |
| `Input/profitability_calc_wip.csv` | Preços atual + mês anterior (12 ações) | **Fonte da verdade** do retorno mensal das ações |
| `Output/output_letter.docx` | Carta v1 (baixa qualidade) | Baseline a superar |
| `enter_challenge.rivet-project` | Grafo Rivet v1 | Reescrito (ver §6) |
| `advisor-high-level-habilities.pdf` | Skills do assessor de elite | "Voz" do agente (tom da carta) |
| `what-makes-a-good-advisor.pdf` | O que faz um bom assessor | "Voz" do agente (tom da carta) |

### Dados-chave do Albert (transcritos do extrato)
- Patrimônio **R$386.858,82** = Investido **R$312.186,20** + Caixa **R$74.672,62**.
- Alocações são % do **investido**: **Ações 19,32%**, **Fundos 67,71%**, **Renda Fixa 12,97%**.
- Perfil tratado como **Conservador** (orientação do cliente/assessor; o documento de
  perfil original marca "Moderado", mas a diretriz é menor exposição a volatilidade).
- Assessor **Antonio Bicudo (A7699)**; snapshot **07/05/2025**.

---

## 3. Diagnóstico do v1 (problemas encontrados)

1. **Caminhos hardcoded** `C:\Users\blope\Downloads\...` → o grafo não roda em outra máquina.
2. **Sem cálculo de rentabilidade real** — o CSV de preços **nem está conectado** ao grafo;
   o "3,5%" da carta v1 é **inventado**.
3. **Macro alucinado** — a carta v1 diz Selic ~9%, "Fed corta em julho", câmbio R$4,70.
   A fonte XP diz **Selic 15,50%**, IPCA 6,1%/2025, **câmbio 6,20**, **sem** cortes do Fed.
4. **Cliente errado** — carta endereçada a **"João"** (hardcoded), mas o cliente é **Albert**.
5. **Sem módulo de compra/venda** — recomendações genéricas, não ligadas ao perfil moderado.
6. **Sem formatação** — saída é texto cru, não uma carta de 2 páginas com identidade visual.
7. **Mistura de horizontes** — retorno *desde o início* dos fundos tratado como se fosse mensal.
   (Ex.: HAPV3 está **−74,6% desde a compra**, mas **+76,4% só no mês** — o v1 confundiria isso.)
8. **Determinismo ausente** — todos os números saíam do LLM (temp 0,5) em vez de uma camada calculada.

---

## 4. Princípio central da arquitetura

> **Separar CÁLCULO de NARRAÇÃO.** Uma camada Python determinística e **testada**
> produz um **JSON de fatos**. O LLM **nunca inventa um número** — só narra os fatos.
> Isso elimina a alucinação (problemas #2, #3) na raiz.

```
Input (CSV, JSON, txt)  ─►  engine/ (Python determinístico, pytest)  ─►  facts.json
                                                                           │
                                              ┌────────────────────────────┤
                                              ▼                            ▼
                                   Rivet (narração LLM, PT)      output/ (PDF identidade XP)
```

### Honestidade técnica (o que NÃO prometemos)
- **"Tempo real de tudo"**: o case pede o **mês passado**; fundos (FICs) não têm cotação
  pública. Fonte da verdade = CSV; CDI/IPCA reais do mês via **BCB SGS** (grátis);
  brapi só para um snapshot **atual** opcional (`--live`), datado, fora do cálculo histórico.
- **"Erro 0%"**: vale para a **aritmética** (testada até o centavo). Fundos sem cota mensal
  são **estimativa** (proxy CDI), explicitamente sinalizada como tal.
- **"Aprendizado contínuo"**: fora de escopo de um PoC; vira roadmap (`REPORT.md`).
- **Identidade XP**: emulamos o *house-style* (paleta amarelo/preto), sem logo oficial.

---

## 5. Cálculo de rentabilidade (mês de referência: abril/2025)

| Classe | Retorno no mês | Base |
|---|---|---|
| **Ações** | **+7,74%** (apurado) | preço atual ÷ preço mês anterior (CSV) |
| **Renda Fixa** | **+0,88%** (apurado) | IPCA real 0,43% + 5,45%a.a. pro-rata |
| **Fundos** | estimado por estratégia (CDI 1,06% / Ibovespa 3,69%) | referência de mercado de cada estratégia |
| **Carteira (total)** | **≈ +2,58%** (estimativa) | soma ponderada das contribuições |

Benchmarks reais (BCB + Yahoo, abr/2025): **CDI 1,06%**, **IPCA 0,43%**, **Ibovespa +3,69%**,
**S&P 500 −0,76%**. Destaques do mês: **HAPV3 +76,4%** e **MRFG3 −16,4%**.

**Rentabilidade acumulada (desde os aportes):** custo R$318.650,59 → atual R$312.186,20 =
**−2,03%**. Por classe: **Ações −38,7%** (puxam para baixo), **Fundos +11,2%**, **Renda
Fixa +34,9%**. É o contraste que sustenta a virada conservadora.

> **Dados dos fundos (decisão de honestidade).** A cota mensal exata de cada fundo "Advisory"
> não é identificável com segurança na base da CVM (cada estratégia tem dezenas de classes;
> ex.: Truxt Long Bias retorna 10 CNPJs, Riza Lotus e Trend Investback retornam 0). Cravar um
> CNPJ errado geraria número falso atribuído a um fundo específico. Por isso estimamos cada
> fundo pela **referência de mercado da sua estratégia** (CDI/Ibovespa), com dado real do mês,
> sem nunca afirmar que algo "não foi fornecido".

> **Disclaimer de janela (também impresso na carta).** Os preços das ações refletem o
> **extrato de 07/05/2025**; os indicadores de mercado (CDI, IPCA, Ibovespa, S&P 500) usam o
> **fechamento do mês de referência**. Por isso as janelas de comparação podem diferir
> ligeiramente — optamos por usar os fechamentos disponíveis em vez do dia específico, com
> esta ressalva explícita na documentação e no relatório do cliente.

---

## 6. Plano de execução (subfases + checkpoints Git)

- [x] **0.** Scaffold + `PLANEJAMENTO.md` + venv/deps.
- [x] **1.** Loaders (`data_loader.py`) + dados de mercado BCB + Yahoo (`market_data.py`).
- [x] **2.** Motor de rentabilidade (`profitability.py`) + **testes pytest**.
- [x] **3.** Motor de recomendações rule-based (`recommendations.py`) + benchmarks + testes.
- [x] **4.** Identidade XP (`engine/brand.py`) + gráficos (`charts.py`) + PDF (`render.py`, reportlab).
- [x] **5.** Camada LLM Anthropic (`llm.py` + `narrate.py`) com narração ancorada + fallback.
- [x] **6.** Grafo Rivet corrigido e completo (Anthropic, facts JSON, sem caminhos hardcoded).
- [x] **7.** CLI (`run.py`), carta final do Albert (PDF), `REPORT.md`, `README.md`. **(42 testes ok)**

## 6.1. Ajustes solicitados (rodadas seguintes)
- **Provider:** validado com chave real. Tanto a narração Python quanto o **grafo Rivet usam
  `claude-sonnet-4-6`** — o modelo confirmado como disponível para a chave da conta (a mesma
  chave do `.env` roda o pipeline e o Rivet sem ajuste). Código provider-flexível (OpenAI também).
- **Perfil conservador:** alocação-alvo 10/30/60 (Ações/Fundos/RF), guardrails mais
  apertados, regra de redução de fundos voláteis. Documentado em `config.POLICY`.
- **Fundos sem "não fornecido":** estimativa por estratégia (CDI/Ibovespa), nunca citando
  ausência de dado (ver decisão de honestidade na §5).
- **Rentabilidade acumulada:** custo dos aportes vs valor atual, por classe e total.
- **Identidade visual:** **logo PNG oficial da XP** (`Input/XP_Investimentos_logo.png`) no
  cabeçalho; rodapé sem menção a "emulação"; gráficos mais limpos e simétricos.
- **Tom humano (anti-IA):** sem travessões/hífens-lista, sem clichês de IA, frases de
  tamanho variado, análise de sentimento conforme o resultado, conexão ao objetivo de longo
  prazo. Pós-processamento remove "traços de IA". Aplicado à carta, ao `REPORT.md` e a esta doc.
- **Câmbio 6,20:** atribuído explicitamente à **projeção da XP** (relatório 06/02/2025).

## 6.2. Ajustes solicitados (rodada de revisão da carta)
- **Rodapé corrigido:** o disclaimer era cortado em 240 caracteres (`disclaimer[120:240]`),
  deixando "fale com o seu" solto. O `render.py` agora faz **quebra por palavra** (nunca corta
  no meio de uma frase). Texto final: *"Material de caráter informativo. Rentabilidade passada
  não garante resultados futuros. Estimativas estão sinalizadas no relatório. Em caso de dúvidas,
  fale com o seu assessor."* (removida a cláusula "não constitui oferta/recomendação" a pedido).
- **Abertura profissional:** o opener emocional ("Sei que ver o resultado... incomoda") foi
  trocado por um enquadramento institucional ("Encaminhamos o relatório de acompanhamento...").
  Ajustados o `SYSTEM_PROMPT` (registro formal) e o fallback determinístico. Removida saudação
  duplicada ("Prezado Albert," que aparecia 2x) e dateline duplicado no corpo.
- **Análise adicional — custo do caixa ocioso:** quantifica quanto o caixa parado deixa de
  render ao CDI do mês (`cash_monthly_carry_brl` ≈ R$ 791,53/mês; ~R$ 10 mil/ano), ancorando a
  recomendação nº 1 (alocar o caixa) com impacto financeiro concreto.
- **Data de emissão (anti-anacronismo):** a carta agora traz um dateline ("São Paulo,
  12 de maio de 2025"), **fixado na linha do tempo do case** (`config.ISSUE_DATE`), nunca no
  relógio do sistema (`datetime.now()` estamparia o ano corrente). O relatório é de **abril/2025**,
  sobre o extrato de **07/05/2025**, logo é enviado em **maio/2025**.

## 6.3. Como o material é entregue (arquitetura × Rivet)
> **O grafo Rivet sozinho NÃO contém os cálculos — isso é intencional.** O Rivet é a camada de
> **narração**: ele lê o `build/facts.json` (produzido pelo motor Python) e escreve a carta. Os
> cálculos de rentabilidade, recomendação e formatação vivem no pacote `engine/` (Python), porque
> número de LLM aluciná. A entrega do case é o **projeto inteiro** (engine + Rivet + dados + docs),
> não só o `.rivet-project`. Ver §"Entrega e escalabilidade" no `README.md`.

## 6.4. Escalabilidade real (N clientes × M assessores × perfis)
Garantia pedida: rodar cálculos **e** análises de forma automatizada para uma base, dado que
cada cliente terá o mesmo conjunto de arquivos de input. Implementado:
- **Política por perfil:** `config.POLICIES` (Conservador/Moderado/Agressivo) + `policy_for()`.
  O `recommendations.analyze()` escolhe a política pelo `risk_profile` do cliente, então alvo de
  alocação, cap por ativo e limites de fundos voláteis **mudam por cliente** (não só os números).
- **Narração perfil-aware:** `narrate._system_prompt(facts)` e o fallback usam nome + perfil do
  cliente; a carta fala "perfil moderado/agressivo" conforme o caso.
- **Runner em lote:** `python -m engine.run --all` varre `data/*.json` e gera uma carta por
  cliente, nomeada por slug em `Output/`. Cliente e **assessor** vêm do próprio JSON.
- **Sem colisão:** gráficos namespaced por cliente (`build_all(facts, prefix=...)`); dados de
  mercado (preços/CDI/IPCA/Ibov) são comuns ao mês e reaproveitados.
- **Saudação por gênero:** campo `gender` → "Prezada/Prezado".
- **Prova:** 2º cliente sintético `data/beatriz_almeida_portfolio.json` (Moderado, assessora
  Carla Menezes). `--all` gera Albert + Beatriz com recomendações distintas. Travado por
  `tests/test_multiclient.py`.
- **Anti-anacronismo mantido:** datas do case fixas em `config` (nunca `datetime.now()`).

## 6.5. Ingestão automática do extrato (fim da transcrição manual)
Última etapa manual eliminada, sem abrir mão do anti-alucinação: `engine/ingest.py`.
- **Princípio:** o LLM propõe a ESTRUTURA; uma camada determinística de RECONCILIAÇÃO confere o
  DINHEIRO. `soma(posições)==investido`, `investido+caixa==patrimônio`, `%da posição==posição/investido`,
  tudo ao centavo (`reconcile()`). Falhou → registro **rejeitado para revisão**, nunca aceito.
- **Parsers determinísticos** de número lidam com os dois formatos do extrato (US `R$386,858.82`
  e PT `R$ 30.000,00`; `%` PT `-41,7%`).
- **Não inventa o que o extrato não tem:** categoria de estratégia do fundo, índice/spread do CDB
  e rating ficam para a etapa de enriquecimento (explícita), não para a extração.
- **Validação:** golden test (`tests/test_ingest.py`) garante que o extrato correto reconcilia e
  que qualquer número adulterado é rejeitado; a extração ao vivo reproduz o JSON do Albert.
- **Total de testes: 42.**

## 6.6. Legibilidade dos nomes de ativos (escalável)
Nomes longos de fundo poluíam a carta. Solução **genérica** (regra, não de-para por fundo, então
vale para milhares de ativos): `facts._short_name()` remove tokens de estrutura jurídica
(FIC/FIM/FIA/FIRF/REF/DI/CP/Advisory, "S.A.", sufixo "- MÊS/ANO" de CDB). Ex.: "Riza Lotus Plus
Advisory FIC FIRF REF DI CP" → "Riza Lotus Plus"; "CDB BANCO C6 CONSIGNADO S.A. - SET/2024" →
"CDB Banco C6". Cada leg ganha `short_name` nos facts. A narração foi instruída a **agrupar fundos
por estratégia** (CDI vs Ibovespa) e citar só 1-2 destaques, em vez de listar todos. O humanizador
ainda troca jargão em inglês que vaza (ex.: "sleeve" → "parcela"). Travado por teste.

## 7. Homologação
- `pytest -q` (todos os cálculos batem com valores conferidos à mão).
- `python -m engine.run --client Albert` gera a carta sem erro.
- Conferência: nome correto (Albert), macro batendo com a fonte XP, ≤2 páginas, PT correto,
  e **todo número da carta existe no `facts.json`**.
