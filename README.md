# AI Financial Advisor — XP / Enter case

PoC que gera, de ponta a ponta, um **relatório mensal de investimentos** (carta em PDF,
em português, com identidade visual XP) para clientes middle-market — a partir do extrato,
do perfil de risco e da macro da casa.

**Princípio:** um motor Python **determinístico e testado** calcula tudo e produz um
`facts.json`; o LLM (Claude) apenas **narra** os fatos e nunca inventa um número.

> 📄 Leia `PLANEJAMENTO.md` (documentação completa + diagnóstico do v1) e `REPORT.md`
> (entregável: problemas, abordagem, próximos passos).

## Resultado (Albert, abril/2025)

- Ações **+7,74%** (apurado pelos preços) · Renda Fixa **+0,88%** (IPCA+spread) ·
  Fundos estimados por estratégia (CDI/Ibovespa) · **Carteira ≈ +2,58%** (estimativa).
- Acumulado desde os aportes: **−2,03%** (Ações −38,7% pesam; RF +34,9% e Fundos +11,2% seguram).
- Benchmarks reais: **CDI 1,06%**, **IPCA 0,43%**, **Ibovespa +3,69%**, **S&P 500 −0,76%**.
- Carta final: `Output/albert_da_silva_relatorio_mensal.pdf` (2 páginas, datada de **12/05/2025**).

## Como rodar

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# pipeline completo (usa fallback determinístico se não houver chave LLM)
python -m engine.run                 # cliente único (Albert)
python -m engine.run --all           # LOTE: gera uma carta por JSON em data/

# narração com LLM (Anthropic Claude): defina a chave e rode
export ANTHROPIC_API_KEY=sk-ant-...           # ou crie um arquivo .env (gitignored)
export ANTHROPIC_MODEL=claude-sonnet-4-6   # opcional
python -m engine.run
# (OpenAI gpt-4o-mini também é suportado via OPENAI_API_KEY)

# opções úteis
python -m engine.run --no-llm        # força narração determinística
python -m engine.run --emit-facts    # (re)escreve build/facts.json (input do Rivet)
python -m engine.run --live          # anexa snapshot de cotação atual (contexto)

# testes (aritmética conferida à mão, 0% de tolerância)
python -m pytest -q
```

## Fluxo Rivet (grounded)

`enter_challenge.rivet-project` é a versão **corrigida e completa** do grafo (o v1 está em
`enter_challenge_v1_backup.rivet-project`). Para usá-lo:

1. `python -m engine.run --emit-facts` → gera `build/facts.json`.
2. Abra o `.rivet-project` no [Rivet](https://rivet.ironcladapp.com/) e configure a
   **Anthropic API key** em *Settings*.
3. Rode o grafo `main_challenge`: ele lê `build/facts.json` + a macro, narra performance /
   macro / recomendações e integra tudo na **carta final em português**.

**Rodar o grafo headless (sem abrir o app):** há um runner Node em `rivet_runner/` que usa
`@ironclad/rivet-node` + o plugin Anthropic:

```bash
cd rivet_runner && npm install        # uma vez
cd .. && python -m engine.run --emit-facts   # gera build/facts.json
node --env-file=.env rivet_runner/run_graph.mjs   # roda o grafo com Claude
```

Validado por execução real: o grafo carrega, resolve os nós `chatAnthropic`, lê o
`facts.json` e chama a API — bastando uma `ANTHROPIC_API_KEY` válida no `.env`.

Correções do v1 embutidas no grafo: sem caminhos `C:\Users\...`; macro restrito à fonte;
cliente parametrizado (Albert, não "João"); nós **Anthropic Claude (Opus `claude-opus-4-6`)**
com prompts **grounded** no `facts.json` (em vez de texto cru a temp 0,5). O logo do header usa
`Input/XP_Investimentos_logo.png`.

## Estrutura

```
engine/            # motor determinístico + narração + render
  config.py        # datas do case, política do perfil, séries BCB
  data_loader.py   # extrato (JSON) + preços (CSV)
  market_data.py   # BCB (CDI/IPCA) + Yahoo (Ibovespa/S&P) + brapi (--live)
  profitability.py # retorno do mês: apurado vs estimado
  recommendations.py # motor rule-based (compra/venda/rebalance)
  facts.py         # contrato de grounding (facts.json)
  ingest.py        # extrato (texto) -> JSON via LLM + reconciliação determinística
  charts.py        # gráficos paleta XP
  brand.py         # tokens de marca XP
  llm.py / narrate.py # Claude + fallback determinístico (perfil-aware)
  render.py        # PDF de 2 páginas (reportlab)
  run.py           # CLI: cliente único ou --all (lote)
  tests/           # 41 testes (inclui multi-cliente/perfil e ingestão)
data/              # 1 JSON por cliente (Albert + Beatriz demo); mesmo schema
Input/ Output/     # insumos do case e carta gerada
*.rivet-project    # grafo v2 (corrigido) + backup do v1
```

## Entrega e escalabilidade (como submeter o case)

**Por que os cálculos não estão no grafo Rivet.** Por decisão de arquitetura, o Rivet é só a
camada de **narração**: ele lê o `build/facts.json` e escreve a carta. Toda a matemática
(rentabilidade, recomendações, render do PDF) vive no pacote Python `engine/`, porque LLM
inventa número — separar cálculo de narração é o que mata a alucinação da v1. Logo, **o
entregável do case é o projeto inteiro**, não apenas o `.rivet-project`:

```
engine/  (cálculo + render)  →  build/facts.json  →  enter_challenge.rivet-project (narração)
        + data/ + Input/ + Output/ + README.md + REPORT.md + PLANEJAMENTO.md
```

Sugestão de submissão: o repositório Git completo (ou um zip) com `REPORT.md` como porta de
entrada (resumo de 2 páginas), a carta final em `Output/`, e o grafo Rivet já apontando para o
`facts.json`. Quem avaliar consegue tanto **ler a carta pronta** quanto **rodar o pipeline**.

**Escalável para N clientes × M assessores × perfis distintos.** O pipeline é parametrizado por
dados, não por código. `python -m engine.run --all` varre `data/*.json` e gera uma carta por
cliente (cálculos **e** análises), nomeada por cliente em `Output/`.

- **Dados, não código:** cada cliente é um JSON em `data/` (schema do `albert_portfolio.json`),
  carregando seu próprio `client` **e** `advisor`. Cabeçalho, rodapé e assinatura do PDF saem
  desses campos: assessor diferente por cliente, sem tocar no código.
- **Análises adaptam ao perfil:** a política (alocação-alvo + guardrails) é escolhida pelo
  `risk_profile` do cliente (`config.policy_for`). Conservador 10/30/60 (cap 5%/ativo),
  Moderado 25/35/40 (cap 8%), Agressivo 45/35/20 (cap 12%). As recomendações e o texto da carta
  refletem o perfil de cada um.
- **Prova no repo:** além do Albert (Conservador, assessor Antonio Bicudo), há um 2º cliente
  sintético `beatriz_almeida` (Moderado, assessora Carla Menezes). `--all` gera as duas cartas,
  cada uma com seu assessor, perfil, alvo de alocação e recomendações próprias.
- **Cálculos compartilhados rodam uma vez:** preços (CSV), CDI/IPCA (BCB) e Ibovespa/S&P (Yahoo)
  são dados de mercado comuns ao mês; o que muda por cliente é o portfólio. Gráficos são
  namespaced por cliente (sem colisão em lote).
- **Ingestão automática (sem transcrição manual):** `python -m engine.ingest "Input/XP - Albert_s portfolio.txt"`
  lê o extrato e o estrutura em JSON via LLM, com **reconciliação determinística** que confere os
  totais ao centavo (soma das posições == investido; investido+caixa == patrimônio; % de cada
  posição == fatia do investido). Se não bate, **rejeita para revisão** em vez de aceitar número
  errado. Validado contra o extrato real do Albert (`engine/ingest.py`).

*Identidade visual XP com logo oficial no cabeçalho. Material informativo —
rentabilidade passada não garante resultados futuros.*
