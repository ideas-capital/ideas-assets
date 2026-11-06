"""Gera o Radar de ativos em dois formatos, para consultar fora do app:

- RADAR.md          -> o GitHub mostra formatado, inclusive no app do celular e
                       em repositório PRIVADO.
- site/index.html   -> página única, leve, para GitHub Pages / Cloudflare Pages.

Uso:  python scripts/gerar_radar.py
Roda sozinho em dias úteis pelo GitHub Actions (.github/workflows/radar-diario.yml).
"""
from __future__ import annotations

import html
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pwass import radar  # noqa: E402
from pwass.engine import strategies as S  # noqa: E402
from pwass.data import market  # noqa: E402

AVISO = "IDEAS CAPITAL assets · uso pessoal · regras fixas; decisão e risco são do usuário."


def pct(x, d=1, sign=True):
    if x is None or pd.isna(x):
        return "—"
    return (f"{x * 100:+.{d}f}%" if sign else f"{x * 100:.{d}f}%").replace(".", ",")


def n(x, d=2):
    if x is None or pd.isna(x):
        return "—"
    return f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def collect() -> dict:
    cfg = yaml.safe_load((ROOT / "config" / "radar.yaml").read_text(encoding="utf-8"))
    df, px = radar.assets(cfg)
    us = radar.us_rates()
    tb = us.loc[us["Indicador"] == "T-Bill 3 meses", "Valor"]
    fx_t = next(iter(cfg.get("cambio", {})), None)
    br = radar.brazil(fx=px[fx_t] if fx_t in px else None, tbill=float(tb.iloc[0]) if len(tb) else None)
    sig = {}
    try:
        m = S.completed_months(S.monthly(market.prices(list(S.MODEL_TICKERS))))
        g = S.gem_explain(m)
        ex = S.gtaa_explain(m)
        sig = {"mes": m.index[-1], "gem": g, "gtaa_in": [t for t in ex.index if ex.loc[t, "Sinal"] == "Manter"],
               "gtaa_out": [t for t in ex.index if ex.loc[t, "Sinal"] != "Manter"]}
    except Exception as e:  # noqa: BLE001
        sig = {"erro": str(e)}
    return {"cfg": cfg, "df": df, "px": px, "us": us, "br": br, "sig": sig,
            "data": px.index[-1], "gerado": datetime.now(timezone.utc)}


def strip_tags(s: str) -> str:
    return s.replace("<b>", "**").replace("</b>", "**")


# ---------------------------------------------------------------- Markdown
def to_markdown(d: dict) -> str:
    df, us, br, sig = d["df"], d["us"], d["br"], d["sig"]
    out = [f"# Radar de ativos — {d['data']:%d/%m/%Y}", "",
           f"_{AVISO} Gerado em {d['gerado']:%d/%m/%Y %H:%M} UTC._", "", "## Painel de prudência"]
    out += [f"- {strip_tags(x)}" for x in radar.summary(df, us, br)]
    if "gem" in sig:
        g = sig["gem"]
        out += ["", f"**Sinais do mês fechado ({sig['mes']:%m/%Y})** — GEM: {S.NAMES[g['pick']]} "
                    f"({g['pick']} / UCITS {g['ucits']}) · GTAA investido em {', '.join(sig['gtaa_in']) or 'nada'}"
                    f"; caixa no lugar de {', '.join(sig['gtaa_out']) or 'nada'}."]
    for gname in d["cfg"]["grupos"]:
        sub = df[df["Grupo"] == gname]
        if sub.empty:
            continue
        out += ["", f"## {gname}", "| Ativo | Leitura | 12m | vs MM200 | RSI | Postura |", "|---|---|---|---|---|---|"]
        for _, r in sub.iterrows():
            out.append(f"| {r['Ativo']} ({r['Ticker']}) | {r['Leitura']} | {pct(r['12 meses'])} | "
                       f"{pct(r['vs MM200'])} | {r['RSI']:.0f} | {r['Postura prudente']} |")
    out += ["", "## Juros e crédito nos EUA", "| Indicador | Valor | Percentil | Leitura |", "|---|---|---|---|"]
    for _, r in us.iterrows():
        out.append(f"| {r['Indicador']} | {n(r['Valor'])} {r['Unidade']} | {r['Percentil']:.0f} "
                   f"(desde {r['Histórico desde']}) | {r['Leitura']} |")
    out += ["", "## Renda fixa Brasil e câmbio", "| Indicador | Valor | Referência |", "|---|---|---|"]
    for k, (v, when) in br.get("indicadores", {}).items():
        out.append(f"| {k} | {n(v)}% | {when} |")
    if "tesouro" in br:
        out += ["", f"**Tesouro Direto ({br['data_tesouro']:%d/%m/%Y})**", "", "| Título | Vencimento | Taxa |",
                "|---|---|---|"]
        for _, r in br["tesouro"].iterrows():
            pre = "Selic + " if r["Titulo"] == "Tesouro Selic" else "IPCA + " if ("IPCA" in r["Titulo"] or "Renda+" in r["Titulo"]) else ""
            out.append(f"| {r['Titulo']} | {r['Vencimento']:%m/%Y} | {pre}{n(r['Taxa'])}% |")
    if "dolar" in br:
        dl = br["dolar"]
        out += ["", f"**Dólar:** R$ {n(dl['preco'], 4)} · {radar.EMOJI[dl['cor']]} {dl['status']} ({dl['motivos']})."
                    " Postura: remessas parceladas."]
    out += ["", "---", "Legenda: 🟢 alta saudável · 🔵 correção/recuperação · 🟡 esticado · 🔴 tendência de baixa. "
                "Regras em `config/radar.yaml`; detalhes na tela *Radar de ativos* do app."]
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------- HTML
CSS = """
:root{--bg:#f7f8fa;--card:#fff;--text:#0f172a;--muted:#64748b;--line:rgba(15,23,42,.09);--accent:#2563eb;
--verde:rgba(34,197,94,.12);--azul:rgba(37,99,235,.07);--amarelo:rgba(245,158,11,.14);--vermelho:rgba(239,68,68,.11)}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#0b1120;--card:#111827;--text:#e5e7eb;
--muted:#94a3b8;--line:rgba(148,163,184,.16);--accent:#60a5fa;--verde:rgba(34,197,94,.16);--azul:rgba(96,165,250,.10);
--amarelo:rgba(245,158,11,.16);--vermelho:rgba(239,68,68,.16)}}
:root[data-theme="dark"]{--bg:#0b1120;--card:#111827;--text:#e5e7eb;--muted:#94a3b8;--line:rgba(148,163,184,.16);
--accent:#60a5fa;--verde:rgba(34,197,94,.16);--azul:rgba(96,165,250,.10);--amarelo:rgba(245,158,11,.16);--vermelho:rgba(239,68,68,.16)}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);
font:15px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
main{max-width:1080px;margin:0 auto;padding:24px 16px 48px}
h1{font-size:1.6rem;margin:0 0 4px}h2{font-size:1.1rem;margin:28px 0 10px}
.sub{color:var(--muted);margin:0 0 18px;font-size:.9rem}
.panel{background:var(--card);border:1px solid var(--line);border-left:4px solid var(--accent);border-radius:12px;padding:14px 16px}
.panel li{margin:4px 0}.panel ul{margin:0;padding-left:18px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:10px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:10px 12px}
.card .t{font-size:.72rem;color:var(--muted);text-transform:uppercase;letter-spacing:.04em}
.card .v{font-size:1.25rem;font-weight:650}
.wrap{overflow-x:auto;background:var(--card);border:1px solid var(--line);border-radius:12px}
table{border-collapse:collapse;width:100%;font-size:.88rem}
th,td{padding:8px 10px;text-align:left;border-bottom:1px solid var(--line);white-space:nowrap}
th{font-size:.74rem;color:var(--muted);font-weight:600;text-transform:uppercase;letter-spacing:.03em}
td.wrapcell{white-space:normal;min-width:220px}td.num{text-align:right;font-variant-numeric:tabular-nums}
tr.verde{background:var(--verde)}tr.azul{background:var(--azul)}tr.amarelo{background:var(--amarelo)}tr.vermelho{background:var(--vermelho)}
footer{color:var(--muted);font-size:.8rem;margin-top:32px}
"""


def _table(headers, rows, classes=None, wrap_cols=(), num_cols=()):
    th = "".join(f"<th>{html.escape(h)}</th>" for h in headers)
    body = []
    for i, r in enumerate(rows):
        cls = f' class="{classes[i]}"' if classes else ""
        tds = "".join(
            f'<td class="{"wrapcell" if j in wrap_cols else "num" if j in num_cols else ""}">{html.escape(str(c))}</td>'
            for j, c in enumerate(r))
        body.append(f"<tr{cls}>{tds}</tr>")
    return f'<div class="wrap"><table><thead><tr>{th}</tr></thead><tbody>{"".join(body)}</tbody></table></div>'


def to_html(d: dict) -> str:
    df, us, br, sig = d["df"], d["us"], d["br"], d["sig"]
    parts = [f"<h1>Radar de ativos</h1><p class='sub'>Dados de {d['data']:%d/%m/%Y} · gerado em "
             f"{d['gerado']:%d/%m/%Y %H:%M} UTC · {AVISO}</p>"]
    items = "".join(f"<li>{x}</li>" for x in radar.summary(df, us, br))
    if "gem" in sig:
        g = sig["gem"]
        items += (f"<li>Sinais do mês fechado ({sig['mes']:%m/%Y}): GEM em <b>{html.escape(S.NAMES[g['pick']])}</b> "
                  f"(UCITS {g['ucits']}); GTAA investido em <b>{', '.join(sig['gtaa_in']) or 'nada'}</b>.</li>")
    parts.append(f"<section class='panel'><b>Painel de prudência</b><ul>{items}</ul></section>")

    counts = df["_cor"].value_counts()
    cards = [("🟢 Alta saudável", counts.get("verde", 0)), ("🔵 Correção / recuperando", counts.get("azul", 0)),
             ("🟡 Esticado", counts.get("amarelo", 0)), ("🔴 Tendência de baixa", counts.get("vermelho", 0))]
    parts.append(f"<h2>Resumo · todos os {len(df)} ativos</h2><div class='grid'>" + "".join(
        f"<div class='card'><div class='t'>{t}</div><div class='v'>{v}</div></div>" for t, v in cards) + "</div>")

    for gname in d["cfg"]["grupos"]:
        sub = df[df["Grupo"] == gname]
        if sub.empty:
            continue
        rows = [[f"{r['Ativo']} ({r['Ticker']})", r["Leitura"], pct(r["12 meses"]), pct(r["vs MM200"]),
                 f"{r['RSI']:.0f}", r["Postura prudente"]] for _, r in sub.iterrows()]
        parts.append(f"<h2>{html.escape(gname)}</h2>" + _table(
            ["Ativo", "Leitura", "12 meses", "vs MM200", "RSI", "Postura prudente"], rows,
            sub["_cor"].tolist(), wrap_cols=(5,), num_cols=(2, 3, 4)))

    rows = [[r["Indicador"], f"{n(r['Valor'])} {r['Unidade']}", f"{r['Percentil']:.0f}", r["Leitura"]]
            for _, r in us.iterrows()]
    parts.append("<h2>Juros e crédito nos EUA</h2>" + _table(
        ["Indicador", "Valor", "Percentil histórico", "Leitura"], rows, us["_cor"].tolist(),
        wrap_cols=(3,), num_cols=(1, 2)))

    ind = br.get("indicadores", {})
    if ind:
        parts.append("<h2>Renda fixa Brasil e câmbio</h2><div class='grid'>" + "".join(
            f"<div class='card'><div class='t'>{html.escape(k)}</div><div class='v'>{n(v)}%</div>"
            f"<div class='sub' style='margin:0'>{html.escape(str(w))}</div></div>" for k, (v, w) in ind.items()) + "</div>")
    if "tesouro" in br:
        rows = []
        for _, r in br["tesouro"].iterrows():
            pre = "Selic + " if r["Titulo"] == "Tesouro Selic" else "IPCA + " if ("IPCA" in r["Titulo"] or "Renda+" in r["Titulo"]) else ""
            rows.append([r["Titulo"], f"{r['Vencimento']:%m/%Y}", f"{pre}{n(r['Taxa'])}%"])
        parts.append(f"<h2>Tesouro Direto · {br['data_tesouro']:%d/%m/%Y}</h2>" + _table(["Título", "Vencimento", "Taxa"], rows))
    if "dolar" in br:
        dl = br["dolar"]
        parts.append(f"<p class='sub' style='margin-top:12px'>Dólar R$ {n(dl['preco'], 4)} · {radar.EMOJI[dl['cor']]} "
                     f"{dl['status']} ({html.escape(dl['motivos'])}). Postura prudente: remessas parceladas.</p>")
    parts.append("<footer>Legenda: 🟢 alta saudável · 🔵 correção/recuperação · 🟡 esticado · 🔴 tendência de baixa. "
                 "Fontes: Yahoo Finance, FRED, Banco Central do Brasil, Tesouro Transparente. "
                 "Gerado pelo PWASS.</footer>")
    return ("<!doctype html><html lang='pt-BR'><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<title>Radar de Ativos</title><style>{CSS}</style></head><body><main>{''.join(parts)}</main></body></html>")


def main() -> None:
    d = collect()
    (ROOT / "RADAR.md").write_text(to_markdown(d), encoding="utf-8")
    site = ROOT / "site"
    site.mkdir(exist_ok=True)
    (site / "index.html").write_text(to_html(d), encoding="utf-8")
    print(f"Radar de {d['data']:%d/%m/%Y}: RADAR.md e site/index.html gravados ({len(d['df'])} ativos).")


if __name__ == "__main__":
    main()
