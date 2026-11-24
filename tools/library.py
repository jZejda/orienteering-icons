"""Validate and build the SVG library with Python's standard library."""
from copy import deepcopy
from decimal import Decimal, InvalidOperation
from pathlib import Path
import hashlib
import html
import json
import re
import shutil
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
SVG = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG)
LEGACY_SOLID = {"boulder", "boulder-field", "rock-pillar"}
ALLOWED_ELEMENTS = {"svg", "g", "path", "line", "circle", "ellipse", "rect", "defs", "pattern", "clipPath", "text"}
ID = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
LOCAL_URL = re.compile(r"url\(#([A-Za-z0-9_.:-]+)\)")


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_catalog():
    return read_json(ROOT / "data/icons.json")


def icons(catalog):
    return [(ref, rep) for ref, entry in catalog["entries"].items()
            for rep in entry["representations"] if rep["type"] == "icon"]


def validate_svg(path, *, legacy=False, layout=False):
    path = Path(path)
    root = ET.parse(path).getroot()
    expected = "0 0 240 32" if layout else "0 0 24 24"
    if root.tag != f"{{{SVG}}}svg" or root.get("viewBox") != expected:
        raise ValueError(f"{path}: expected an SVG with viewBox={expected!r}")
    ids, references = [], []
    for element in root.iter():
        if element.tag.removeprefix(f"{{{SVG}}}") not in ALLOWED_ELEMENTS:
            raise ValueError(f"{path}: unsupported element {element.tag}")
        if element.get("id"):
            ids.append(element.get("id"))
        for attribute, value in element.attrib.items():
            if attribute.startswith("on") or attribute.endswith("href") or attribute == "style":
                raise ValueError(f"{path}: unsupported attribute {attribute}")
            references.extend(LOCAL_URL.findall(value))
            if "url(" in value and not LOCAL_URL.fullmatch(value):
                raise ValueError(f"{path}: only local SVG references are allowed")
            if attribute in {"fill", "stroke", "color"}:
                allowed = value in {"none", "currentColor"} or LOCAL_URL.fullmatch(value)
                exception = (legacy and path.stem in LEGACY_SOLID and element is root
                             and attribute == "fill" and value == "solid")
                if not allowed and not exception:
                    raise ValueError(f"{path}: unexpected {attribute}={value!r}")
    if len(ids) != len(set(ids)) or set(references) - set(ids):
        raise ValueError(f"{path}: duplicate IDs or unresolved references")
    return root


def validate(catalog=None):
    catalog = load_catalog() if catalog is None else catalog
    legacy = read_json(ROOT / "data/legacy-icons.json")
    for source, digest in legacy.items():
        if hashlib.sha256((ROOT / source).read_bytes()).hexdigest() != digest:
            raise ValueError(f"Protected legacy icon changed: {source}")
    expected = {f"{group}.{n}" for group, count in
                [(0, 5), (1, 16), (2, 10), (3, 11), (4, 10), (5, 24), (6, 2),
                 (8, 11), (9, 4), (10, 2), (11, 1), (12, 14), (13, 3),
                 (14, 1), (15, 6), (16, 3)] for n in range(1, count + 1)}
    if set(catalog["entries"]) != expected:
        raise ValueError("The catalog must cover the numbered IOF references (excluding 7.n)")
    seen, sources = set(), set()
    for ref, rep in icons(catalog):
        public_id = rep["symbolId"]
        if not ID.fullmatch(public_id) or public_id in seen:
            raise ValueError(f"Duplicate or invalid public ID: {public_id}")
        seen.add(public_id)
        sources.add(rep["source"])
        validate_svg(ROOT / rep["source"], legacy=rep["source"] in legacy)
    actual = {str(p.relative_to(ROOT)) for folder in [ROOT / "icons", ROOT / "variants/iof-2024"]
              for p in folder.glob("*.svg")}
    if sources != actual:
        raise ValueError(f"Icon inventory mismatch: {sorted(sources ^ actual)}")
    for alias in catalog["aliases"]:
        if not ID.fullmatch(alias["id"]) or alias["id"] in seen or alias["target"] not in seen:
            raise ValueError(f"Invalid alias: {alias}")
        seen.add(alias["id"])
    layouts = read_json(ROOT / "data/layouts.json")
    for ref, entry in catalog["entries"].items():
        if not entry["representations"]:
            raise ValueError(f"No representation for {ref}")
        for rep in entry["representations"]:
            if rep["type"] == "layout-template":
                root = validate_svg(ROOT / rep["source"], layout=True)
                fields = [el for el in root.iter() if el.get("data-field") == "distance"]
                if len(fields) != int(layouts[ref]["distanceRequired"]):
                    raise ValueError(f"{ref}: incorrect distance placeholders")
                if any((el.text or "").strip() for el in fields):
                    raise ValueError(f"{ref}: distance must not be hard-coded")
            elif rep["type"] == "dynamic-layout" and layouts[ref]["type"] != "dimension":
                raise ValueError(f"{ref}: missing dynamic dimension definition")
    return {"icons": len(icons(catalog)), "aliases": len(catalog["aliases"]),
            "references": len(expected), "legacyPreserved": len(legacy),
            "routeTemplates": sum(x["type"] == "route" for x in layouts.values()),
            "dynamicDimensions": sum(x["type"] == "dimension" for x in layouts.values())}


def _rewrite_ids(root, prefix):
    replacements = {el.get("id"): prefix + "--" + el.get("id")
                    for el in root.iter() if el.get("id")}
    for element in root.iter():
        for attribute, value in list(element.attrib.items()):
            if attribute == "id":
                element.set(attribute, replacements[value])
            else:
                element.set(attribute, LOCAL_URL.sub(lambda m: "url(#" + replacements[m[1]] + ")", value))


def sprite(catalog=None):
    catalog = load_catalog() if catalog is None else catalog
    result = ET.Element(f"{{{SVG}}}svg")
    definitions = {}
    for _, rep in icons(catalog):
        node = ET.parse(ROOT / rep["source"]).getroot()
        _rewrite_ids(node, rep["symbolId"])
        node.tag = f"{{{SVG}}}symbol"
        node.set("id", rep["symbolId"])
        for attribute in ["width", "height"]:
            node.attrib.pop(attribute, None)
        # An invalid fill has no computed value. Omitting it preserves inheritance,
        # unlike replacing it with currentColor, which changes old consumer behavior.
        if node.get("fill") == "solid":
            node.attrib.pop("fill")
        result.append(node)
        definitions[rep["symbolId"]] = node
    for alias in catalog["aliases"]:
        node = deepcopy(definitions[alias["target"]])
        _rewrite_ids(node, alias["id"])
        node.set("id", alias["id"])
        result.append(node)
    return result


def _number(value):
    if isinstance(value, bool):
        raise ValueError("Values must be non-negative decimal numbers")
    try:
        value = Decimal(str(value))
    except InvalidOperation as error:
        raise ValueError("Values must be non-negative decimal numbers") from error
    if not value.is_finite() or value < 0:
        raise ValueError("Values must be finite and non-negative")
    result = format(value.normalize(), "f") if value else "0"
    if len(result) > 8:
        raise ValueError("Value is too long to fit in the description layout")
    return result


def render_layout(reference, *, values=None, distance=None):
    layouts = read_json(ROOT / "data/layouts.json")
    if reference not in layouts:
        raise ValueError(f"Unknown layout: {reference}")
    definition = layouts[reference]
    if definition["type"] == "route":
        if values is not None or definition["distanceRequired"] != (distance is not None):
            raise ValueError("Supply distance only for a route that requires it")
        root = ET.parse(ROOT / definition["source"]).getroot()
        for element in root.iter():
            if element.get("data-field") == "distance":
                element.text = _number(distance) + " m"
                element.attrib.pop("data-field")
                if len(element.text) > 6:
                    element.set("textLength", "62")
                    element.set("lengthAdjust", "spacingAndGlyphs")
        return root
    if distance is not None or values is None or len(values) != definition["valueCount"]:
        raise ValueError(f"{reference} requires {definition['valueCount']} dimension value(s)")
    numbers = [_number(v) for v in values]
    root = ET.Element(f"{{{SVG}}}svg", {"width": "24", "height": "24", "viewBox": "0 0 24 24",
                          "fill": "none", "stroke": "currentColor", "stroke-width": "2"})

    def text(x, y, value, size="9"):
        attrs = {"x": str(x), "y": str(y), "text-anchor": "middle", "font-family": "sans-serif",
                 "font-size": size, "fill": "currentColor", "stroke": "none"}
        if len(value) > 4:
            attrs.update({"textLength": "18" if reference != "9.3" else "9", "lengthAdjust": "spacingAndGlyphs"})
        element = ET.SubElement(root, f"{{{SVG}}}text", attrs)
        element.text = value
    if reference == "9.1":
        text(12, 16, numbers[0])
    elif reference == "9.2":
        text(12, 16, " × ".join(numbers), "8")
    elif reference == "9.3":
        ET.SubElement(root, f"{{{SVG}}}path", {"d": "M4 20 20 4", "stroke-width": "1.5"})
        text(7, 9, numbers[0], "7")
        text(17, 21, numbers[1], "7")
    else:
        text(12, 9, numbers[0])
        text(12, 21, numbers[1])
    return root


def _preview(catalog):
    cards = []
    for ref, rep in icons(catalog):
        samples = []
        for theme in ["light", "dark", "accent"]:
            root = ET.parse(ROOT / rep["source"]).getroot()
            _rewrite_ids(root, rep["symbolId"] + "-" + theme)
            samples.append(f'<span class="{theme}">{ET.tostring(root, encoding="unicode")}</span>')
        samples.append('<span class="external"><svg viewBox="0 0 24 24"><use href="#'
                       + rep["symbolId"] + '"/></svg></span>')
        cards.append('<article><small>IOF ' + ref + '</small><h2>' + html.escape(rep["symbolId"])
                     + '</h2><div class="samples">' + ''.join(samples) + '</div></article>')
    for ref, definition in read_json(ROOT / "data/layouts.json").items():
        values = {"9.1": ["2.5"], "9.2": [8, 4], "9.3": ["0.5", 3], "9.4": [2, 3]}
        root = render_layout(ref, values=values[ref]) if ref in values else render_layout(ref, distance=definition["exampleDistanceM"])
        cards.append('<article><small>IOF ' + ref + ' · dynamic example</small><div class="layout">'
                     + ET.tostring(root, encoding="unicode") + '</div></article>')
    inline_sprite = ET.tostring(sprite(catalog), encoding="unicode").replace('<svg ', '<svg aria-hidden="true" style="position:absolute;width:0;height:0;overflow:hidden" ', 1)
    return '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Orienteering Icons — local preview</title><style>
body{font:14px system-ui;background:#eef1f6;color:#152132;margin:24px}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:16px}article{background:white;padding:18px;border:1px solid #d4dce5}h2{font-size:16px;overflow-wrap:anywhere}.samples{display:flex;gap:8px}.samples span{display:flex;width:60px;height:60px;align-items:center;justify-content:center;fill:none}.samples svg{width:40px;height:40px}.dark{background:#182132;color:#f4f7ff}.accent{color:#c21c67}.external{background:#fff;color:#152132}.external svg{fill:none;stroke:currentColor;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}.layout svg{max-width:100%;height:48px}small{color:#53677b}</style><h1>IOF Control Descriptions 2024 — local preview</h1><p>Light / dark / accent / sprite use. Historical IDs are preserved; corrected legacy drawings use an -iof-2024 suffix. External href and xlink:href are checked separately by tools/check-browser.cjs.</p>''' + inline_sprite + '<main>' + ''.join(cards) + '</main></html>'


def build(destination=None):
    catalog = load_catalog()
    summary = validate(catalog)
    destination = Path(destination) if destination else ROOT / "dist"
    destination.mkdir(parents=True, exist_ok=True)
    payload = ET.tostring(sprite(catalog), encoding="utf-8", xml_declaration=True)
    for name in ["ioficons-sprite.svg", "ioficon-sprite.svg", "iofico.svg"]:
        (destination / name).write_bytes(payload)
    metadata = deepcopy(catalog)
    for _, rep in icons(metadata):
        output = "icons/" + rep["symbolId"] + ".svg"
        (destination / "icons").mkdir(exist_ok=True)
        # Keep individual legacy SVGs byte-identical too; opt-in fixes are separate.
        shutil.copyfile(ROOT / rep["source"], destination / output)
        rep["file"] = output
    for alias in catalog["aliases"]:
        target = next(rep for _, rep in icons(catalog) if rep["symbolId"] == alias["target"])
        shutil.copyfile(ROOT / target["source"], destination / "icons" / (alias["id"] + ".svg"))
    for entry in catalog["entries"].values():
        for rep in entry["representations"]:
            if rep["type"] == "layout-template":
                out = destination / rep["source"]
                out.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / rep["source"], out)
    for entry in metadata["entries"].values():
        for rep in entry["representations"]:
            if rep["type"] == "layout-template":
                rep["file"] = rep["source"]
            elif rep["type"] == "dynamic-layout":
                rep["file"] = "layouts.json"
    (destination / "catalog.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n")
    shutil.copyfile(ROOT / "data/layouts.json", destination / "layouts.json")
    shutil.copyfile(ROOT / "LICENSE", destination / "LICENSE")
    shutil.copyfile(ROOT / "NOTICE", destination / "NOTICE")
    (destination / "preview.html").write_text(_preview(catalog), encoding="utf-8")
    (destination / "validation.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary
