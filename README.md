# Orienteering Icons

SVG pictograms for IOF Control Descriptions 2024. The library contains 116 base
icons: 38 preserved originals and 78 additions. Four opt-in variants correct
legacy drawings without replacing their original names or files. This is a
local implementation of the specification, not an IOF-certified reproduction.

## Build and preview

Python 3.9 or newer is sufficient; the build uses only the standard library.

```sh
python3 tools/build.py --check
python3 -m unittest discover -s tests -v
python3 tools/build.py
python3 -m http.server 8000 --directory dist
```

Open `http://localhost:8000/preview.html` to inspect light, dark, accent and
sprite rendering. The preview also opens directly as a local file. The generated `dist/` directory contains individual
SVGs, a sprite, catalog metadata, route templates and the preview.

Optional browser regression checks use Playwright and Sharp:

```sh
node tools/check-browser.cjs
python3 tools/review.py
```

The check needs `playwright` and `sharp` available to Node and a Chromium browser
installed by Playwright. Set `IOF_CHROME` to use a different Chrome executable.
It checks both `href` and `xlink:href`, four color/fill contexts, and 64 diagnostic
flag-location rotations. Results and the before/after review go into `output/revision/`.
The before/after review additionally requires the original local `handoff/`
archive, which is deliberately excluded from this integration commit.

`ioficons-sprite.svg` is the canonical sprite filename. `ioficon-sprite.svg`
and `iofico.svg` contain identical bytes for compatibility with earlier examples
and consumers. Serve the sprite from the same origin as the consuming page.

## Use

```html
<svg class="ioficons" viewBox="0 0 24 24" aria-hidden="true">
  <use href="path/to/ioficons-sprite.svg#spur"/>
</svg>
```

```css
.ioficons {
  width: 24px;
  height: 24px;
  stroke: currentColor;
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
  fill: none;
}
```

Existing fragment names remain available. `xlink:href` continues to work for
older consumers; new markup can use `href`. The misspelled
`minor-wather-channel` is preserved, with `minor-water-channel` as an additional
alias of the same drawing.

## Legacy drawing compatibility

The original files in `icons/` are preserved byte-for-byte and checked against
`data/legacy-icons.json`. In particular, the original `boulder` remains a circle.
Use these explicit variants for revised drawings:

| Existing ID | Revised ID | Change |
| --- | --- | --- |
| `boulder` | `boulder-iof-2024` | Filled triangle matching the reference motif |
| `rock-pillar` | `rock-pillar-iof-2024` | Explicit `currentColor` fill |
| `boulder-field` | `boulder-field-iof-2024` | Explicit `currentColor` fills |
| `knoll` | `knoll-iof-2024` | Filled point instead of concentric strokes |

Three original SVGs contain invalid `fill="solid"`. The sprite build omits that
invalid attribute, preserving its inherited-fill behavior. It does not silently
replace it with `currentColor`. Consumers that filled the old solid symbols
through CSS can keep doing so, or select the explicit revised variants.

The showcase website already has an empty `boulder-cluster` ID. This library
supplies its drawing, but this task does not update or deploy that website.

## Catalog and directions

`data/icons.json` uses official IOF reference numbers as string keys. Category,
column, direction and appearance are separate fields. Multiple representations
can share a reference: `15.6`, for example, has both an icon and a wide row.
The generated catalog adds a `file` field pointing into `dist/`.

Directional flag-location icons retain their documented example orientations.
`baseDirection` records the actual orientation; the corresponding rotation is
`targetAngle - baseAngle`, clockwise around `(12, 12)`. No additional directional
IDs are generated automatically. Bend is a shape orientation, not a flag compass
direction. The catalog distinguishes extra directions in column C from the
specification's numbered examples rather than inventing new IOF numbers.

## Dynamic dimensions and route rows

Dimensions `9.1`–`9.4` contain variable numeric values and are rendered on demand:

```sh
python3 tools/render.py 9.1 --values 2.5 --output /tmp/height.svg
python3 tools/render.py 9.2 --values 8 4 --output /tmp/size.svg
python3 tools/render.py 9.3 --values 0.5 3 --output /tmp/slope.svg
python3 tools/render.py 9.4 --values 2 3 --output /tmp/between.svg
python3 tools/render.py 15.1 --distance 60 --output /tmp/taped-away.svg
python3 tools/render.py 15.3 --output /tmp/crossing.svg
```

The Python API is `render_layout(reference, values=[...], distance=...)` in
`tools/library.py`; it returns an XML element. Values are finite, non-negative
decimal numbers in metres. The renderer rejects missing or unexpected fields
and values too long to fit the layout. Illustrative distances remain metadata
examples, not fixed SVG text.

Wide rows live in `templates/routes/` with `viewBox="0 0 240 32"`. They are never
included as standalone 24×24 sprite symbols. Use the renderer to populate the
distance placeholder before displaying a row.

## Source and rights

The original MIT [LICENSE](LICENSE) is retained unchanged. [NOTICE](NOTICE)
records the IOF reference and the unresolved provenance of the additional
drawings before a public release. The IOF PDF and its reference artwork are not
included in the built library. `handoff/` remains the untouched historical input;
`data/revisions.json` records which proposed drawings changed and why.
