"""Turn the grounded FACTS into the letter's Portuguese prose.

Two paths, same contract (a dict with keys greeting/performance/macro/
recommendations/closing):

  - LLM path (Claude): writes in the voice of an elite XP advisor, STRICTLY from
    the facts (never inventing a number). Prompt is in English (case constraint);
    the letter output is Brazilian Portuguese.
  - Deterministic fallback: composes grounded prose directly from the facts, so
    the whole pipeline runs (and is testable) with no API key.
"""
from __future__ import annotations

import json

from . import config, llm

SECTIONS = ["greeting", "performance", "macro", "recommendations", "closing"]

# The advisor "voice" distilled from advisor-high-level-habilities.pdf and
# what-makes-a-good-advisor.pdf: empathetic, clear, proactive, trustworthy,
# jargon-light, always tying advice to the client's profile and goals.
SYSTEM_PROMPT = """You are an elite investment advisor at XP Investimentos writing \
a monthly client letter. Voice: trustworthy, clear, proactive and empathetic; \
explain in plain language (a "middle-market" client), never condescending. \

ABSOLUTE RULES:
- Write in Brazilian Portuguese (the client letter must be in pt-BR).
- Ground EVERY figure strictly in the provided FACTS JSON. NEVER invent or alter \
a number, name, date or macro figure. If a figure is flagged as an estimate, \
present it transparently as an estimate.
- Do not contradict the macro facts (e.g., Selic, IPCA, FX) — use them verbatim.
- Be concise: the whole letter must fit two pages. No headers, no markdown, no \
bullet symbols inside the prose — return clean paragraphs only.
- Address the client by first name. Sign-off is handled by the template (do not \
add a signature).

Return ONLY a JSON object with these string keys: greeting, performance, macro, \
recommendations, closing. Each value is 1 short paragraph (greeting ~2 sentences; \
performance ~5-6 sentences; macro ~4 sentences; recommendations ~4 sentences; \
closing ~2 sentences)."""


def _user_prompt(facts: dict) -> str:
    return (
        "Write the five paragraphs from these FACTS. Highlight that the equities "
        "sleeve return is MEASURED while the fund (and total) figure is an "
        "ESTIMATE (CDI proxy, monthly fund NAV not provided). Connect the macro "
        "scenario (high Selic, pressured inflation) to the recommendations "
        "(deploy idle cash, increase fixed income, trim concentration, review the "
        "impaired non-dividend stock). FACTS JSON:\n\n"
        + json.dumps(facts, ensure_ascii=False)
    )


# --------------------------------------------------------------- deterministic
def _fallback(facts: dict) -> dict:
    c = facts["client"]
    t = facts["totals"]
    p = facts["performance"]
    b = facts["benchmarks"]
    m = facts["macro"]
    month = facts["meta"]["reference_month_label"]
    best, worst = p["highlight_best"], p["highlight_worst"]

    def _p(v):
        return f"{v:+.2f}%".replace(".", ",")

    def _brl(v):
        return ("R$ " + f"{v:,.2f}").replace(",", "X").replace(".", ",").replace("X", ".")

    greeting = (
        f"É com satisfação que compartilhamos o relatório de {month}, com o "
        f"desempenho da sua carteira e o cenário que pode influenciá-la nos "
        f"próximos meses. Como sempre, nossas orientações seguem alinhadas ao seu "
        f"perfil {c['risk_profile'].lower()} e aos seus objetivos de longo prazo."
    )

    performance = (
        f"No mês, a parcela de ações — que apuramos diretamente pelos preços — "
        f"rendeu {_p(p['equities_return_pct'])}, com destaque para {best['ticker']} "
        f"({_p(best['monthly_return_pct'])}) e o desempenho negativo de "
        f"{worst['ticker']} ({_p(worst['monthly_return_pct'])}). A renda fixa "
        f"avançou {_p(p['fixed_income_return_pct'])}, em linha com a inflação e o "
        f"carrego do CDB. Para os fundos (cerca de dois terços da carteira), a cota "
        f"mensal não consta nos dados deste fechamento; assim, o retorno total "
        f"estimado de {_p(p['total_return_pct'])} usa uma referência conservadora "
        f"de CDI para essa parcela e deve ser lido como estimativa. Ainda assim, o "
        f"resultado supera o CDI do mês em {_p(p['excess_cdi_pp'])} ponto(s) e "
        f"representa um ganho real de {_p(p['real_return_pct'])} acima da inflação. "
        f"Seu patrimônio total soma {_brl(t['patrimony_brl'])}."
    )

    macro = (
        f"No pano de fundo, a XP projeta Selic terminal de "
        f"{m['selic_terminal_pct']:.2f}% e inflação (IPCA) de {m['ipca_2025_pct']:.1f}% "
        f"em 2025, com câmbio ao redor de R$ {m['fx_end_2025']:.2f} e crescimento do "
        f"PIB de {m['pib_2025_pct']:.1f}%. O quadro é de juros altos por um período "
        f"prolongado e incerteza fiscal e eleitoral elevada, sem cortes de juros nos "
        f"EUA no cenário base. Esse ambiente favorece a renda fixa pós-fixada e exige "
        f"seletividade na bolsa. É o contexto que orienta os ajustes sugeridos a seguir."
    )

    recs = facts["recommendations"][:4]
    rec_clauses = "; ".join(r["headline"][0].lower() + r["headline"][1:] for r in recs)
    recommendations = (
        f"Diante desse cenário e do seu perfil, priorizamos quatro frentes: "
        f"{rec_clauses}. O caixa parado de {_brl(t['cash_brl'])} "
        f"({t['cash_ratio_pct']:.1f}% do patrimônio) tem alto custo de oportunidade "
        f"com a Selic atual, e a carteira está sobrealocada em fundos e leve em renda "
        f"fixa frente ao alvo do perfil moderado. Os detalhes de cada ação e o plano "
        f"de rebalanceamento seguem no quadro abaixo."
    )

    closing = (
        f"Seguimos à disposição para revisar estas recomendações em conjunto e "
        f"ajustar o que fizer sentido para os seus objetivos. Agradecemos pela "
        f"confiança e seguimos comprometidos com o crescimento sustentável do seu "
        f"patrimônio."
    )

    return {"greeting": greeting, "performance": performance, "macro": macro,
            "recommendations": recommendations, "closing": closing}


# ----------------------------------------------------------------------- main
def build_narrative(facts: dict, use_llm: bool | None = None) -> dict:
    """Return the 5 narrative sections. Uses Claude when a key is available."""
    if use_llm is None:
        use_llm = llm.have_key()
    if use_llm:
        try:
            raw = llm.complete(SYSTEM_PROMPT, _user_prompt(facts))
            data = json.loads(raw[raw.find("{"): raw.rfind("}") + 1])
            if all(k in data and isinstance(data[k], str) for k in SECTIONS):
                data["_source"] = "anthropic"
                return data
        except Exception as exc:  # any LLM/parse error -> safe fallback
            fb = _fallback(facts)
            fb["_source"] = f"fallback ({type(exc).__name__})"
            return fb
    fb = _fallback(facts)
    fb["_source"] = "deterministic-fallback"
    return fb


if __name__ == "__main__":
    from .facts import build_facts
    nar = build_narrative(build_facts())
    print("source:", nar["_source"], "\n")
    for k in SECTIONS:
        print(f"### {k}\n{nar[k]}\n")
