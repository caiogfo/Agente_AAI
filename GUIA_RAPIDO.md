# Guia rápido para rodar (passo a passo, do zero)

Para quem **nunca rodou um projeto** assim. Em ~15 minutos você gera a carta em PDF.
Os comandos são para **macOS**; ao final há as diferenças para **Windows**.

> Você vai precisar de: um computador, a **chave da Anthropic** (o responsável pelo
> projeto te envia) e seguir os passos abaixo na ordem. Não precisa saber programar.

---

## Passo 1 — Receber o projeto

O repositório é **privado**, então uma destas duas formas:

- **(Mais fácil) Receber um arquivo `.zip`** com o projeto. Salve em algum lugar fácil
  (ex.: a Mesa/Desktop) e **descompacte** (clique duplo). Vai virar uma pasta chamada
  `Agente_AAI`.
- **Ou** receber um convite de acesso no GitHub: abra o link do repositório, clique no
  botão verde **`Code` → `Download ZIP`**, e descompacte como acima.

Ao final deste passo você tem uma pasta `Agente_AAI` no computador.

## Passo 2 — Instalar o Python (se ainda não tiver)

1. Abra o programa **Terminal** (no Mac: aperte `Cmd + Espaço`, digite "Terminal", Enter).
2. Digite o comando abaixo e aperte Enter para checar se já tem Python:

   ```bash
   python3 --version
   ```

   - Se aparecer algo como `Python 3.9` (ou maior), **pule para o Passo 3**.
   - Se der erro/"command not found", baixe o instalador em
     <https://www.python.org/downloads/> , instale normalmente (avançar/avançar) e
     feche e reabra o Terminal.

## Passo 3 — Entrar na pasta do projeto pelo Terminal

No Terminal, digite `cd ` (com um espaço depois), **arraste a pasta `Agente_AAI`** para
dentro da janela do Terminal (isso cola o caminho) e aperte Enter:

```bash
cd /caminho/que/apareceu/Agente_AAI
```

Para conferir que está no lugar certo, digite `ls` e Enter: você deve ver nomes como
`engine`, `README.md`, `Makefile`.

## Passo 4 — Preparar o ambiente (uma única vez)

Copie e cole este comando, Enter, e **aguarde** terminar (baixa as dependências):

```bash
make setup
```

> Se aparecer "make: command not found", use este comando equivalente no lugar:
> ```bash
> python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt && cp .env.example .env
> ```

## Passo 5 — Colar a chave da Anthropic

O passo anterior criou um arquivo chamado **`.env`** dentro da pasta. Abra ele num editor
de texto e cole a chave que você recebeu, assim:

```
ANTHROPIC_API_KEY=cole-a-chave-aqui
```

Salve o arquivo. (Para abrir pelo Terminal no Mac: `open -e .env`.)

> **Não tem a chave?** Tudo bem: o projeto roda mesmo assim, só que o texto da carta é
> gerado por um modo automático (sem IA). Os números e o layout ficam idênticos.

## Passo 6 — Gerar a carta

```bash
make run
```

(sem `make`: `./.venv/bin/python -m engine.run`)

Quando terminar, a carta em PDF estará na pasta **`Output/`**, com nome
`albert_da_silva_relatorio_mensal.pdf`. Abra com dois cliques.

Para gerar a carta de **todos os clientes** de uma vez (ex.: Albert e Beatriz):

```bash
make batch
```

---

## Deu algum erro? (soluções rápidas)

- **`command not found: python3`** → o Python não está instalado ou o Terminal não foi
  reaberto. Refaça o Passo 2 e abra um Terminal novo.
- **`make: command not found`** → use os comandos alternativos indicados nos Passos 4 e 6.
- **`No such file or directory`** → você não está na pasta do projeto. Refaça o Passo 3.
- **Erro de chave / API** → confira se colou a chave certa no `.env` (Passo 5). Se quiser,
  é só deixar sem chave que ele usa o modo automático.

## Windows (diferenças)

- Abra o **PowerShell** (menu Iniciar → "PowerShell").
- No Passo 2, ao instalar o Python, **marque a caixa "Add Python to PATH"**.
- Não há `make`. Use:
  ```powershell
  python -m venv .venv
  .\.venv\Scripts\pip install -r requirements.txt
  copy .env.example .env
  .\.venv\Scripts\python -m engine.run
  ```
- A carta sai na pasta `Output\` do mesmo jeito.
