# Guia de execução

Passo a passo direto para rodar o projeto e gerar a carta em PDF. Cada comando vem
comentado com o que ele faz. Tempo total: ~5 minutos.

> **Pré-requisitos:** Python 3.9+ e um terminal. A chave da Anthropic é **opcional**
> para gerar a carta (há narração determinística de fallback), mas é **necessária para
> rodar o grafo Rivet** — ela vem anexada no corpo do e-mail desta entrega.

---

## 1. Entrar na pasta do projeto

```bash
cd caminho/para/Agente_AAI      # raiz do projeto (onde estão README.md e Makefile)
```

## 2. Preparar o ambiente (uma única vez)

```bash
make setup
```

O `make setup` faz três coisas: cria um ambiente virtual isolado em `.venv/`, instala as
dependências de `requirements.txt` e gera o arquivo `.env` (a partir de `.env.example`)
onde a chave será colada no próximo passo.

> Sem `make`? Comando equivalente:
> ```bash
> python3 -m venv .venv \
>   && ./.venv/bin/pip install -r requirements.txt \
>   && cp .env.example .env
> ```

## 3. Colar a chave da Anthropic

Abra o `.env` (criado no passo anterior) e cole a chave recebida no e-mail:

```bash
ANTHROPIC_API_KEY=cole-a-chave-aqui
ANTHROPIC_MODEL=claude-sonnet-4-6      # já vem assim; é o modelo validado p/ esta chave
```

Salve. (No Mac dá para abrir pelo terminal com `open -e .env`.)

> **Sem a chave a carta ainda sai:** a narração cai no modo determinístico. Os números,
> os gráficos e o layout ficam idênticos — só o texto deixa de ser escrito pelo Claude.

## 4. Gerar a carta

```bash
make run        # gera a carta do cliente padrão (Albert) em Output/
```

A carta sai em `Output/albert_da_silva_relatorio_mensal.pdf` (2 páginas, identidade XP).

Para gerar **todos os clientes** de uma vez (prova de escala — Albert + Beatriz):

```bash
make batch      # varre data/*.json e gera uma carta por cliente
```

> Sem `make`: `./.venv/bin/python -m engine.run` (single) ou `... --all` (lote).

## 5. (Opcional) Rodar o grafo Rivet

O grafo é a **camada de narração**: lê o `facts.json` produzido pelo motor Python e
escreve a carta com o Claude. Precisa da chave no `.env`.

```bash
./.venv/bin/python -m engine.run --emit-facts   # 1) gera build/facts.json (os fatos)
cd rivet_runner && npm install && cd ..          # 2) instala o runner Node (uma vez)
node --env-file=.env rivet_runner/run_graph.mjs  # 3) roda o grafo com o Claude
```

Ou abra `enter_challenge.rivet-project` no app do [Rivet](https://rivet.ironcladapp.com/),
configure a Anthropic key em *Settings* e rode o grafo `main_challenge`.

## 6. (Opcional) Conferir os testes

```bash
make test       # roda os 42 testes (aritmética conferida ao centavo, anti-regressão)
```

---

## Saída

| Arquivo | O que é |
|---|---|
| `Output/albert_da_silva_relatorio_mensal.pdf` | Carta final do cliente real (Albert) |
| `Output/beatriz_almeida_relatorio_mensal.pdf` | 2º cliente (prova de escala), gerado por `make batch` |
| `build/facts.json` | Fatos calculados que alimentam a narração (gerado por `--emit-facts`) |

## Problemas comuns

- **`command not found: python3`** → instale o Python 3.9+ e reabra o terminal.
- **`make: command not found`** → use os comandos equivalentes indicados em cada passo.
- **`No such file or directory`** → você não está na raiz do projeto (refaça o passo 1).
- **Erro de API / chave** → confira a chave no `.env`. Sem chave, o projeto roda no modo
  determinístico mesmo assim.

## Windows (diferenças)

Use o **PowerShell** e, ao instalar o Python, marque **"Add Python to PATH"**. Não há
`make`; rode os comandos manuais:

```powershell
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
copy .env.example .env
# cole a chave no .env, então:
.\.venv\Scripts\python -m engine.run
```
