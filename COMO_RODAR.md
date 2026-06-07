# Como rodar

Passo a passo direto para gerar a carta em PDF. Cada comando vem comentado com o que
faz. Tempo total: ~5 minutos.

> **Pré-requisitos:** Python 3.9+ e um terminal. A chave da Anthropic é **opcional**
> para gerar a carta (há narração determinística de fallback), mas é **necessária para
> rodar o grafo Rivet**, ela vem anexada no corpo do e-mail desta entrega.

## Estrutura das pastas

```
.
├── Carta_Final_Cliente_Albert.pdf   ← carta pronta do Albert (entregável)
├── Carta_Final_Cliente_Beatriz_Sintetica.pdf  ← 2º cliente, sintético (prova de escala)
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

Abra o `.env` com o comando abaixo (dentro de `02_Projeto/`):

```bash
open -a TextEdit .env
```

O arquivo abrirá no TextEdit. Cole a chave no campo indicado:

```
ANTHROPIC_API_KEY=cole-a-chave-aqui
ANTHROPIC_MODEL=claude-opus-4-8        # já vem assim; o Opus mais potente, validado p/ esta chave
```

Salve (`Cmd + S`) e feche.

> **Sem a chave a carta ainda sai:** a narração cai no modo determinístico. Números,
> gráficos e layout ficam idênticos, só o texto deixa de ser escrito pelo Claude.

## 4. Gerar a carta

```bash
make run        # gera UMA carta (cliente padrão, Albert)
```

A carta sai em `02_Projeto/Output/`. Abra com:

```bash
open Output/albert_da_silva_relatorio_abr25.pdf
```

> **Onde as cartas aparecem (importante):** `make run` gera **uma só** carta, a do Albert,
> em `02_Projeto/Output/albert_da_silva_relatorio_abr25.pdf`. Para gerar **as duas** (Albert
> e Beatriz), use **`make batch`** (seção "Vários clientes" abaixo): elas saem juntas em
> `02_Projeto/Output/`, como `albert_da_silva_relatorio_abr25.pdf` e
> `beatriz_almeida_relatorio_abr25.pdf`. As cartas na **raiz** (`Carta_Final_Cliente_*.pdf`)
> são o snapshot já pronto da entrega; rodar o projeto produz a versão datada em `Output/`.
>
> O nome do arquivo leva o **sufixo do mês/ano de referência** (`abr25` = abril/2025),
> derivado automaticamente do período do relatório.
>
> **Mês parametrizável:** para reportar outro mês, use `--month AAAA-MM` (ou a variável
> `REPORT_MONTH`). O mês escolhido define o rótulo da carta, o sufixo do arquivo, a janela dos
> indicadores e as datas do documento. Ex.:
> ```bash
> ./.venv/bin/python -m engine.run --month 2025-05   # gera ..._relatorio_mai25.pdf
> ```
> (O mês do case, `2025-04`, é o padrão e roda offline; outros meses buscam os indicadores ao vivo.)

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
make test       # roda os 73 testes (aritmética conferida ao centavo, anti-regressão)
```

---

## Vários clientes (escala), o ponto central do case

O pipeline é **dirigido por dados, não por código**: cada cliente é um JSON em
`02_Projeto/data/`, com seu próprio cliente **e** assessor. Um comando gera a base inteira:

```bash
make batch      # varre data/*.json e gera UMA carta por cliente em Output/
```

Com os dois clientes do repositório, isso produz **as duas cartas** em `02_Projeto/Output/`:

```
02_Projeto/Output/albert_da_silva_relatorio_abr25.pdf      # Albert (Conservador)
02_Projeto/Output/beatriz_almeida_relatorio_abr25.pdf      # Beatriz (Moderado, sintético)
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

É o mesmo `make batch` para 2 ou para milhares de clientes, muda só a pasta `data/`.

---

## Problemas comuns

- **`command not found: python3`** → instale o Python 3.9+ e reabra o terminal.
- **`make: command not found`** → use os comandos equivalentes indicados em cada passo.
- **`No such file or directory`** → você não está em `02_Projeto/` (refaça o passo 1).
- **Erro de API / chave** → confira a chave no `.env`. Sem chave, roda no modo
  determinístico mesmo assim.

## Windows (passo a passo completo)

Os comandos abaixo substituem os do guia Mac. A lógica é idêntica; só o terminal e os
caminhos mudam.

**Pré-requisito:** ao instalar o Python 3.9+, marque **"Add Python to PATH"** na tela
de instalação. Sem isso, os comandos abaixo não funcionam.

### 1. Abrir o terminal na pasta do projeto

Pressione `Win + S` → digite `PowerShell` → Enter. Depois entre na pasta `02_Projeto`
(ajuste o caminho para onde você salvou o projeto):

```powershell
cd caminho\para\Agente_AAI\02_Projeto    # daqui rodam todos os comandos
```

### 2. Preparar o ambiente (uma única vez)

Não há `make` no Windows. Rode os três comandos abaixo em sequência:

```powershell
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
copy .env.example .env
```

O primeiro cria o ambiente virtual em `.venv\`, o segundo instala as dependências e o
terceiro gera o arquivo `.env` onde a chave será colada no próximo passo.

### 3. Colar a chave da Anthropic

Abra o `.env` com o Bloco de Notas:

```powershell
notepad .env
```

O arquivo abrirá no Bloco de Notas. Cole a chave no campo indicado:

```
ANTHROPIC_API_KEY=cole-a-chave-aqui
ANTHROPIC_MODEL=claude-opus-4-8        # já vem assim; o Opus mais potente, validado p/ esta chave
```

Salve (`Ctrl + S`) e feche.

> **Sem a chave a carta ainda sai:** a narração cai no modo determinístico. Números,
> gráficos e layout ficam idênticos, só o texto deixa de ser escrito pelo Claude.

### 4. Gerar a carta

```powershell
.\.venv\Scripts\python -m engine.run
```

A carta sai em `02_Projeto\Output\`. Abra com:

```powershell
start Output\albert_da_silva_relatorio_abr25.pdf
```

> **Onde as cartas aparecem (importante):** o comando acima gera **uma só** carta, a do
> Albert, em `02_Projeto\Output\albert_da_silva_relatorio_abr25.pdf`. Para gerar **as
> duas** (Albert e Beatriz), use o comando de lote da seção "Vários clientes" abaixo.
> As cartas na **raiz** (`Carta_Final_Cliente_*.pdf`) são o snapshot já pronto da
> entrega; rodar o projeto produz a versão datada em `Output\`.
>
> O nome do arquivo leva o **sufixo do mês/ano de referência** (`abr25` = abril/2025),
> derivado automaticamente do período do relatório.
>
> **Mês parametrizável:** para reportar outro mês, use `--month AAAA-MM`. Ex.:
> ```powershell
> .\.venv\Scripts\python -m engine.run --month 2025-05   # gera ..._relatorio_mai25.pdf
> ```
> (O mês do case, `2025-04`, é o padrão e roda offline; outros meses buscam os indicadores ao vivo.)

### 5. (Opcional) Rodar o grafo Rivet

```powershell
.\.venv\Scripts\python -m engine.run --emit-facts        # 1) gera build/facts.json
cd rivet_runner ; npm install ; cd ..                    # 2) instala o runner Node (uma vez)
node --env-file=.env rivet_runner/run_graph.mjs          # 3) roda o grafo com o Claude
```

> Ou abra `03_Rivet\enter_challenge.rivet-project` no app do
> [Rivet](https://rivet.ironcladapp.com/), configure a Anthropic key em *Settings* e
> rode o grafo `main_challenge_v2`.

### 6. (Opcional) Conferir os testes

```powershell
.\.venv\Scripts\python -m pytest -q    # roda os 73 testes (aritmética conferida ao centavo)
```

### Vários clientes (lote) no Windows

```powershell
.\.venv\Scripts\python -m engine.run --all    # gera uma carta por cliente em data\
```

As cartas saem em `02_Projeto\Output\`, uma por cliente.

### Problemas comuns no Windows

- **`python` não reconhecido** → reinstale o Python marcando "Add Python to PATH" e
  reabra o PowerShell.
- **`Scripts\pip` bloqueado por política de execução** → rode antes:
  `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` e confirme com `S`.
- **`No such file or directory`** → você não está em `02_Projeto\` (refaça o passo 1).
- **Erro de API / chave** → confira a chave no `.env`. Sem chave, roda no modo
  determinístico mesmo assim.
