# PLANEJAMENTO — AI Financial Advisor para clientes XP (case Enter)

> Documento de planejamento e documentação completa do material do case.
> Autor da solução: candidato (case técnico Enter). Cliente tema: XP Investimentos.

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
- Perfil **Moderado**; assessor **Antonio Bicudo (A7699)**; snapshot **07/05/2025**.

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
| **Fundos** | +1,06% (**estimativa**, proxy CDI) | cota mensal não fornecida nos dados |
| **Carteira (total)** | **≈ +2,32%** (estimativa) | soma ponderada das contribuições |

Benchmarks reais (BCB, abr/2025): **CDI 1,06%**, **IPCA 0,43%** → retorno real ≈ **+1,89%**,
**+1,26 p.p. vs CDI**. Cobertura apurada (sem estimativa): **32,29%** do investido.
Destaques do mês: **HAPV3 +76,4%** (recuperação) e **MRFG3 −16,4%**.

> **Disclaimer de janela (também impresso na carta).** Os preços das ações refletem o
> **extrato de 07/05/2025**; os indicadores de mercado (CDI, IPCA, Ibovespa, S&P 500) usam o
> **fechamento do mês de referência**. Por isso as janelas de comparação podem diferir
> ligeiramente — optamos por usar os fechamentos disponíveis em vez do dia específico, com
> esta ressalva explícita na documentação e no relatório do cliente.

---

## 6. Plano de execução (subfases + checkpoints Git)

- [x] **0.** Scaffold + `PLANEJAMENTO.md` + venv/deps.
- [x] **1.** Loaders (`data_loader.py`) + dados de mercado BCB (`market_data.py`).
- [x] **2.** Motor de rentabilidade (`profitability.py`) + **testes pytest** (16/16 ok).
- [ ] **3.** Motor de recomendações rule-based (`recommendations.py`) + benchmarks + testes.
- [ ] **4.** Identidade XP (`output/brand_xp.py`) + gráficos (`charts.py`) + PDF (reportlab).
- [ ] **5.** Camada LLM Anthropic (`llm.py` + `narrate.py`) com narração ancorada nos fatos.
- [ ] **6.** Grafo Rivet corrigido e completo (Anthropic, facts JSON, sem caminhos hardcoded).
- [ ] **7.** CLI (`run.py`), carta final do Albert (PDF), `REPORT.md`, `README.md`.

## 7. Homologação
- `pytest -q` (todos os cálculos batem com valores conferidos à mão).
- `python -m engine.run --client Albert` gera a carta sem erro.
- Conferência: nome correto (Albert), macro batendo com a fonte XP, ≤2 páginas, PT correto,
  e **todo número da carta existe no `facts.json`**.
