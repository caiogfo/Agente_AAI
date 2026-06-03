# AI Financial Advisor (case Enter/XP) — atalhos de execução.
# Uso típico:  make setup  &&  make run        (ou make batch / make test)
# Tudo funciona SEM chave de API (narração determinística). Para narração via
# Claude, exporte ANTHROPIC_API_KEY (ou crie um .env; veja .env.example).

PY  := .venv/bin/python
PIP := .venv/bin/pip
STATEMENT := ../01_Insumos_do_case/XP - Albert_s portfolio.txt

.PHONY: help setup run batch ingest test clean
.DEFAULT_GOAL := help

help:            ## Lista os comandos disponíveis
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN{FS=":.*?## "}{printf "  make %-10s %s\n", $$1, $$2}'

setup:           ## Cria o venv, instala as dependências e prepara o .env
	python3 -m venv .venv && $(PIP) install --quiet --upgrade pip && $(PIP) install -r requirements.txt
	@test -f .env || cp .env.example .env
	@echo "✓ Ambiente pronto."
	@echo "  → Cole a ANTHROPIC_API_KEY no arquivo .env (já criado) e rode: make run"
	@echo "  → Sem chave também funciona (narração determinística)."

run:             ## Gera a carta do cliente padrão (Albert)
	$(PY) -m engine.run

batch:           ## Gera uma carta por cliente em data/*.json (lote)
	$(PY) -m engine.run --all

ingest:          ## Demonstra a ingestão do extrato real + reconciliação
	$(PY) -m engine.ingest "$(STATEMENT)"

test:            ## Roda a suíte de testes
	$(PY) -m pytest -q

clean:           ## Remove artefatos gerados (build/, caches)
	rm -rf build .pytest_cache
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
	@echo "✓ Limpo."
