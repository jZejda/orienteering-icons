#!/usr/bin/env python3
"""Generate a local before/after review; no IOF reference artwork is bundled."""
from pathlib import Path
import hashlib
import html
import json
import xml.etree.ElementTree as ET
from library import ROOT, render_layout, read_json

CHANGES = {
    "boulder-cluster": "Tři překrývající se trojúhelníky s oddělenou přední základnou.",
    "firm-ground-in-marsh": "Odstraněna šipka; mezi čarami zůstává symetrický negativní prostor.",
    "linear-thicket": "Průhledné kruhy a spojnice rozdělená pod jejich obrysy; žádná bílá výplň.",
    "paved-area": "Šrafování tvoří přímo úsečky. Barva se dědí i přes externí use; žádné interní ID patternu.",
    "railway": "Zkrácené a posunuté kolejnice i příčky; celý tah má rezervu uvnitř viewBox.",
    "copse": "Dvě koruny místo tří vrcholů; zachovány dva kmeny.",
    "track-path": "Tři stejně dlouhé úseky; odstraněna koncová tečka a závislost na délce dasharray.",
    "broad-leaved": "Pět čitelných oblých laloků a samostatný krátký kmen bez překřížení.",
    "spring": "Otevřená smyčka u zdroje a oddělené navazující vlny; odstraněno zalomení původní koncové křivky.",
    "map-flip": "Jednotná plná návratová šipka kolem listu; doplněna samostatná reprezentace IOF 15.6 v katalogu.",
    "edge": "Jihovýchodní značka nyní protíná obvod kruhu i z jeho vnitřní strany.",
    "end": "Zkrácený diagonální konec zajišťuje rezervu při všech osmi diagnostických rotacích.",
    "directional-foot": "Zmenšený kruh a zkrácená značka obnovují mezeru a prostor pro otáčení.",
}


def svg(path):
    return Path(path).read_text(encoding="utf-8")


def main():
    output = ROOT / "output/revision"
    output.mkdir(parents=True, exist_ok=True)
    revisions = read_json(ROOT / "data/revisions.json")
    cards = []
    for row in revisions["changes"]:
        if not row["geometryChanged"]:
            continue
        row["changeSummary"] = CHANGES[row["id"]]
        row["afterSha256"] = hashlib.sha256((ROOT / row["source"]).read_bytes()).hexdigest()
        before, after = svg(ROOT / row["handoff"]), svg(ROOT / row["source"])
        cards.append(f'<article><small>IOF {row["iof"]}</small><h3>{row["id"]}</h3><div class="samples"><figure>{before}<figcaption>Před</figcaption></figure><figure>{after}<figcaption>Po</figcaption></figure><figure class="dark">{after}<figcaption>Po · tmavé</figcaption></figure></div><p>{html.escape(CHANGES[row["id"]])}</p></article>')
    legacy = []
    for name, ref in [("boulder", "2.4"), ("rock-pillar", "2.2"), ("boulder-field", "2.5"), ("knoll", "1.10")]:
        before, after = svg(ROOT / "icons" / (name + ".svg")), svg(ROOT / "variants/iof-2024" / (name + ".svg"))
        legacy.append(f'<article><small>IOF {ref} · samostatná varianta</small><h3>{name} → {name}-iof-2024</h3><div class="samples"><figure>{before}<figcaption>Původní ID</figcaption></figure><figure>{after}<figcaption>Nové ID</figcaption></figure><figure class="dark">{after}<figcaption>Nové · tmavé</figcaption></figure></div><p>Původní soubor i jeho ID zůstaly zachovány. Nová kresba se použije pouze výběrem nového ID.</p></article>')
    routes = []
    manifest = read_json(ROOT / "handoff/imports/metadata/batch-06-manifest.json")
    for row in manifest:
        before = svg(ROOT / "handoff/imports" / row["file"])
        after = ET.tostring(render_layout(row["iof"], distance=row["example_distance_m"]), encoding="unicode")
        routes.append(f'<article><h3>IOF {row["iof"]} · {html.escape(row["name_en"])}</h3><div class="route"><small>Před</small>{before}<small>Po · vzdálenost je vstupní hodnota</small>{after}</div></article>')
    summary = read_json(output / "browser-results.json")["summary"] if (output / "browser-results.json").exists() else None
    tests = (f'{summary["comparisons"]} porovnání inline / externí use, {summary["rotationChecks"]} rotací, '
             f'{len(summary["failures"])} rozdílů nad toleranci, {len(summary["rotationFailures"])} ořezů při rotaci.' if summary else 'Browser test dosud nebyl proveden.')
    style = '''*{box-sizing:border-box}body{font:16px/1.65 system-ui;margin:0;background:#eef2f7;color:#152132}header,section,nav{max-width:1160px;margin:auto;padding:28px}h1{font-size:36px;line-height:1.2}h2{font-size:27px}h3{font-size:18px;line-height:1.4;overflow-wrap:anywhere}.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px}article{background:white;border:1px solid #d5dde8;padding:20px;min-width:0}small{color:#52657b}.samples{display:flex;gap:12px}figure{margin:0;width:120px;height:125px;display:flex;align-items:center;justify-content:center;flex-direction:column}figure svg{width:72px;height:72px}figcaption{font-size:12px;margin-top:8px}.dark{background:#182132;color:#f4f7ff}.route svg{display:block;width:100%;height:auto;margin:8px 0 18px}nav{display:flex;gap:24px;flex-wrap:wrap}a{color:#1c579f}code{font:13px ui-monospace,monospace}.banner{background:white;border-left:4px solid #28713c;padding:18px}p{margin:12px 0}.grid p{font-size:14px}@media(max-width:850px){.grid{grid-template-columns:1fr}header,section,nav{padding:20px}.samples{gap:8px}figure{width:90px;height:110px}figure svg{width:64px;height:64px}h1{font-size:29px}}'''
    page = f'''<!doctype html><html lang="cs"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Revize ikon IOF 2024 — před a po</title><style>{style}</style><header><small>ORIENTEERING ICONS · LOKÁLNÍ REVIZE · 24. 11. 2026</small><h1>Opravy a revize připravené ke kontrole</h1><p>Upraveno 13 nových kreseb, přidány 4 samostatné opravené varianty původních ikon a přepracováno 10 instrukčních řádků. Původních 38 SVG i celý handoff zůstaly beze změny.</p><p class="banner">{tests}</p><p>Vstupem byly návrhy z handoffu a stejná dostupná kopie IOF PDF jako při auditu. Níže je původní a upravená kresba; <a href="https://orienteering.sport/iof/rules/control-descriptions/">oficiální předloha</a> zůstává samostatným referenčním dokumentem. Nejde o certifikaci IOF ani vyřešení provenience pro veřejné vydání.</p></header><nav><a href="#new">13 upravených ikon</a><a href="#legacy">4 původní varianty</a><a href="#routes">10 řádků</a><a href="../../dist/preview.html">Všechny ikony</a><a href="browser-results.json">Výsledky testů</a></nav><section id="new"><h2>Nové kresby: před a po</h2><div class="grid">{''.join(cards)}</div></section><section id="legacy"><h2>Opravené původní kresby pod novými ID</h2><div class="grid">{''.join(legacy)}</div></section><section id="routes"><h2>Široké řádky</h2><p>Ukázkové vzdálenosti v tomto přehledu dodal renderer. Zdrojové šablony pevná čísla neobsahují. Všechny řádky mají vlastní viewBox 240×32 a nepatří do 24×24 sprite.</p><div class="grid">{''.join(routes)}</div></section><section><h2>Jak poslat připomínku ke kresbě</h2><p>Stačí název ikony a konkrétní změna, například „spring — zmenšit horní smyčku“ nebo „broad-leaved — širší koruna“. Nejvíce prostoru pro subjektivní doladění zůstává u těchto dvou oblých motivů. Žádný další podklad nyní neblokuje technickou integraci.</p><p>Bez commitu, push nebo změny webu. Historický audit zůstal v output/audit; tento přehled zachycuje stav po opravách.</p></section></html>'''
    (output / "review.html").write_text(page, encoding="utf-8")
    (ROOT / "data/revisions.json").write_text(json.dumps(revisions, ensure_ascii=False, indent=2) + "\n")
    print(output / "review.html")


if __name__ == "__main__":
    main()
