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
  Fundos **+1,06%** (estimativa, proxy CDI, sinalizada) · **Carteira ≈ +2,32%** (estimativa).
- Benchmarks reais: **CDI 1,06%**, **IPCA 0,43%**, **Ibovespa +3,69%**, **S&P 500 −0,76%**.
- Carta final: `Output/Albert_relatorio_mensal.pdf` (2 páginas).

## Como rodar

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# pipeline completo (usa fallback determinístico se não houver chave LLM)
python -m engine.run

# narração com LLM (Anthropic Claude): defina a chave e rode
export ANTHROPIC_API_KEY=sk-ant-...           # ou crie um arquivo .env (gitignored)
export ANTHROPIC_MODEL=claude-sonnet-4-20250514   # opcional
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
cliente parametrizado (Albert, não "João"); nós **Anthropic Claude** com prompts **grounded**
no `facts.json` (em vez de texto cru a temp 0,5).

## Estrutura

```
engine/            # motor determinístico + narração + render
  config.py        # datas do case, política do perfil, séries BCB
  data_loader.py   # extrato (JSON) + preços (CSV)
  market_data.py   # BCB (CDI/IPCA) + Yahoo (Ibovespa/S&P) + brapi (--live)
  profitability.py # retorno do mês: apurado vs estimado
  recommendations.py # motor rule-based (compra/venda/rebalance)
  facts.py         # contrato de grounding (facts.json)
  charts.py        # gráficos paleta XP
  brand.py         # tokens de marca XP
  llm.py / narrate.py # Claude + fallback determinístico
  render.py        # PDF de 2 páginas (reportlab)
  run.py           # CLI
  tests/           # 31 testes
data/              # extrato transcrito (canonical schema)
Input/ Output/     # insumos do case e carta gerada
*.rivet-project    # grafo v2 (corrigido) + backup do v1
```

*Identidade visual em estilo XP (emulação, sem ativos oficiais). Material informativo —
rentabilidade passada não garante resultados futuros.*
