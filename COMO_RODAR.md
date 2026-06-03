# Como rodar

Passo a passo direto para gerar a carta em PDF. Cada comando vem comentado com o que
faz. Tempo total: ~5 minutos.

> **Pré-requisitos:** Python 3.9+ e um terminal. A chave da Anthropic é **opcional**
> para gerar a carta (há narração determinística de fallback), mas é **necessária para
> rodar o grafo Rivet** — ela vem anexada no corpo do e-mail desta entrega.

## Estrutura das pastas

```
.
├── Carta_Final_Cliente_Albert.pdf   ← a carta pronta (entregável)
├── COMO_RODAR.md                    ← este guia
├── REPORT.md                        ← resumo do case (2 páginas)
├── 01_Insumos_do_case/              ← arquivos originais do case (extrato, macro, perfil…)
├── 02_Projeto/                      ← TODO o código roda aqui (engine, dados, saída, Rivet runner)
├── 03_Rivet/                        ← grafos Rivet (final + backup da v1)
└── 04_Planejamento/                 ← documentação de planejamento do projeto
```

**Tudo que se executa fica em `02_Projeto/`.** Os comandos abaixo são rodados de lá.

---

## 1. Abrir o terminal na pasta do projeto

No Mac: `Cmd + Espaço` → digite `Terminal` → Enter. Depois entre na pasta `02_Projeto`
(ajuste o caminho para onde você salvou o projeto):

```bash
cd caminho/para/Agente_AAI/02_Projeto    # daqui rodam todos os comandos
```

## 2. Preparar o ambiente (uma única vez)

```bash
make setup
```

Cria um ambiente virtual isolado em `.venv/`, instala as dependências de
`requirements.txt` e gera o arquivo `.env` (a partir de `.env.example`) onde a chave
será colada no próximo passo.

> Sem `make`? Comando equivalente:
> ```bash
> python3 -m venv .venv \
>   && ./.venv/bin/pip install -r requirements.txt \
>   && cp .env.example .env
> ```

## 3. Colar a chave da Anthropic

Abra o `.env` (criado no passo anterior, dentro de `02_Projeto/`) e cole a chave do e-mail:

```bash
ANTHROPIC_API_KEY=cole-a-chave-aqui
ANTHROPIC_MODEL=claude-sonnet-4-6      # já vem assim; é o modelo validado p/ esta chave
```

Salve. (No Mac: `open -e .env`.)

> **Sem a chave a carta ainda sai:** a narração cai no modo determinístico. Números,
> gráficos e layout ficam idênticos — só o texto deixa de ser escrito pelo Claude.

## 4. Gerar a carta

```bash
make run        # gera a carta do cliente padrão (Albert) em 02_Projeto/Output/
```

Abra o PDF gerado:

```bash
open Output/albert_da_silva_relatorio_mensal.pdf
```

## 5. (Opcional) Rodar o grafo Rivet

O grafo é a **camada de narração**: lê o `facts.json` produzido pelo motor Python e
escreve a carta com o Claude. Precisa da chave no `.env`. Rode tudo de `02_Projeto/`:

```bash
./.venv/bin/python -m engine.run --emit-facts   # 1) gera build/facts.json (os fatos)
cd rivet_runner && npm install && cd ..          # 2) instala o runner Node (uma vez)
node --env-file=.env rivet_runner/run_graph.mjs  # 3) roda o grafo (em 03_Rivet/) com o Claude
```

> Ou abra `03_Rivet/enter_challenge.rivet-project` no app do
> [Rivet](https://rivet.ironcladapp.com/), configure a Anthropic key em *Settings* e
> rode o grafo `main_challenge_v2`.

## 6. (Opcional) Conferir os testes

```bash
make test       # roda os 42 testes (aritmética conferida ao centavo, anti-regressão)
```

---

## Vários clientes (escala) — o ponto central do case

O pipeline é **dirigido por dados, não por código**: cada cliente é um JSON em
`02_Projeto/data/`, com seu próprio cliente **e** assessor. Um comando gera a base inteira:

```bash
make batch      # varre data/*.json e gera UMA carta por cliente em Output/
```

Para **adicionar um cliente novo**, basta soltar mais um JSON em `data/` (mesmo schema do
`albert_portfolio.json`) e rodar `make batch` de novo. Sem tocar no código:

- **Cabeçalho, rodapé e assinatura** saem do JSON → cada cliente pode ter um **assessor
  diferente** (nome, código, gênero → "Assessor/Assessora", "Prezado/Prezada").
- **As análises se adaptam ao perfil**: a política de alocação-alvo e os limites de risco
  são escolhidos pelo campo `risk_profile` (Conservador / Moderado / Agressivo). Logo as
  **recomendações e o texto** mudam por cliente, não só os números.
- **Prova no repositório:** além do Albert (Conservador, assessor Antonio Bicudo), há a
  Beatriz Almeida (Moderado, assessora Carla Menezes). `make batch` gera as duas cartas,
  cada uma com seu plano. Os gráficos são isolados por cliente (sem colisão em lote).

É o mesmo `make batch` para 2 ou para milhares de clientes — muda só a pasta `data/`.

---

## Problemas comuns

- **`command not found: python3`** → instale o Python 3.9+ e reabra o terminal.
- **`make: command not found`** → use os comandos equivalentes indicados em cada passo.
- **`No such file or directory`** → você não está em `02_Projeto/` (refaça o passo 1).
- **Erro de API / chave** → confira a chave no `.env`. Sem chave, roda no modo
  determinístico mesmo assim.

## Windows (diferenças)

Use o **PowerShell** e, ao instalar o Python, marque **"Add Python to PATH"**. Não há
`make`; de dentro de `02_Projeto\` rode:

```powershell
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
copy .env.example .env
# cole a chave no .env, então:
.\.venv\Scripts\python -m engine.run
```
