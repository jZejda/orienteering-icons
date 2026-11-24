/* Optional browser regression check: requires playwright and sharp on NODE_PATH. */
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const assert = require('node:assert/strict');
const { chromium } = require('playwright');
const sharp = require('sharp');

const root = path.resolve(__dirname, '..');
const dist = path.join(root, 'dist');
const output = path.join(root, 'output/revision');
const catalog = JSON.parse(fs.readFileSync(path.join(dist, 'catalog.json'), 'utf8'));
const records = Object.entries(catalog.entries).flatMap(([reference, entry]) =>
  entry.representations.filter(r => r.type === 'icon').map(r => ({ ...r, reference })));
for (const alias of catalog.aliases) {
  records.push({ ...records.find(r => r.symbolId === alias.target), symbolId: alias.id, file: `icons/${alias.id}.svg` });
}
const angles = { n: 0, ne: 45, e: 90, se: 135, s: 180, sw: 225, w: 270, nw: 315 };
const cards = records.map(r => `<article data-id="${r.symbolId}"><header>${r.reference} · ${r.symbolId}</header><div class="pair"><span class="sample direct">${fs.readFileSync(path.join(dist, r.file), 'utf8')}</span><span class="sample external"><svg viewBox="0 0 24 24"><use href="/ioficons-sprite.svg#${r.symbolId}"/></svg></span></div></article>`).join('');
const rotations = records.filter(r => r.baseDirection && r.reference.startsWith('12.')).flatMap(r =>
  Object.entries(angles).map(([direction, target]) => {
    const source = fs.readFileSync(path.join(dist, r.file), 'utf8');
    const body = source.slice(source.indexOf('>') + 1, source.lastIndexOf('</svg>'));
    return `<article data-rotation="${r.symbolId}:${direction}"><header>${r.symbolId} · ${direction}</header><div class="rotation"><svg xmlns="http://www.w3.org/2000/svg" viewBox="-4 -4 32 32" width="128" height="128"><g fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" transform="rotate(${target - angles[r.baseDirection]} 12 12)">${body}</g></svg></div></article>`;
  })).join('');
const fixture = `<!doctype html><meta charset="utf-8"><style>body{font:13px system-ui;margin:24px;color:#152132;background:#fff}main{display:grid;grid-template-columns:repeat(3,360px);gap:16px}article{border:1px solid #ccd4de;padding:12px}header{height:38px}.pair{display:flex;gap:12px}.sample{display:flex;flex:none;width:64px;height:64px;align-items:center;justify-content:center;fill:none;background:#fff;color:#152132}.sample svg{width:48px;height:48px}.external svg{fill:inherit;stroke:currentColor;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}.rotation{width:128px;height:128px;color:#152132;background:white}</style><h1>Browser checks · inline / external use</h1><main>${cards}</main><h1>Flag-location rotations · diagnostic only</h1><main>${rotations}</main>`;

function cropBox(rect) {
  return { left: Math.round(rect.x), top: Math.round(rect.y), width: Math.round(rect.width), height: Math.round(rect.height) };
}

(async () => {
  fs.mkdirSync(output, { recursive: true });
  const server = http.createServer((req, res) => {
    const url = new URL(req.url, 'http://localhost');
    if (url.pathname === '/checks.html') { res.setHeader('Content-Type', 'text/html; charset=utf-8'); res.end(fixture); return; }
    const name = path.resolve(dist, '.' + decodeURIComponent(url.pathname));
    if (!name.startsWith(dist + path.sep)) { res.writeHead(403); res.end(); return; }
    try { res.setHeader('Content-Type', name.endsWith('.svg') ? 'image/svg+xml' : 'text/html'); res.end(fs.readFileSync(name)); }
    catch { res.writeHead(404); res.end(); }
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  let browser;
  try {
    browser = await chromium.launch({ headless: true, executablePath: process.env.IOF_CHROME || undefined });
    const page = await browser.newPage({ viewport: { width: 1200, height: 1000 }, deviceScaleFactor: 1 });
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    page.on('response', response => { if (response.status() >= 400) errors.push(`${response.status()} ${response.url()}`); });
    await page.goto(`http://127.0.0.1:${server.address().port}/checks.html`);
    await page.waitForLoadState('networkidle');
    const sourceOverflows = await page.evaluate(() => [...document.querySelectorAll('article[data-id]')].flatMap(card => {
      const svg = card.querySelector('.direct svg');
      const outside = [...svg.querySelectorAll('path,line,circle,ellipse,rect')].some(el => {
        if (el.closest('defs')) return false;
        const b = el.getBBox(), style = getComputedStyle(el);
        const pad = style.stroke === 'none' ? 0 : parseFloat(style.strokeWidth) / 2;
        return b.x - pad < -0.000001 || b.y - pad < -0.000001 || b.x + b.width + pad > 24.000001 || b.y + b.height + pad > 24.000001;
      });
      return outside ? [card.dataset.id] : [];
    }));
    const positions = await page.evaluate(() => [...document.querySelectorAll('article[data-id]')].map(card => ({
      id: card.dataset.id, boxes: [...card.querySelectorAll('.sample')].map(el => {
        const b = el.getBoundingClientRect(); return { x: b.x + scrollX, y: b.y + scrollY, width: b.width, height: b.height };
      })
    })));
    const results = [];
    const palettes = [
      { name: 'light', foreground: [21, 33, 50], background: [255, 255, 255] },
      { name: 'dark', foreground: [244, 247, 255], background: [24, 33, 50] },
      { name: 'accent', foreground: [194, 28, 103], background: [255, 255, 255] },
      { name: 'legacy-solid', foreground: [194, 28, 103], background: [255, 255, 255] },
    ];
    for (const link of ['href', 'xlink:href']) {
      await page.evaluate(link => document.querySelectorAll('.external use').forEach(use => {
        const url = '/ioficons-sprite.svg#' + use.closest('article').dataset.id;
        use.removeAttribute('href'); use.removeAttributeNS('http://www.w3.org/1999/xlink', 'href');
        if (link === 'href') use.setAttribute('href', url);
        else use.setAttributeNS('http://www.w3.org/1999/xlink', 'xlink:href', url);
      }), link);
      for (const palette of palettes) {
        await page.evaluate(p => document.querySelectorAll('.sample').forEach(el => {
          el.style.color = `rgb(${p.foreground})`; el.style.background = `rgb(${p.background})`;
          el.style.fill = p.name === 'legacy-solid' && ['boulder', 'boulder-field', 'rock-pillar'].includes(el.closest('article').dataset.id) ? 'currentColor' : 'none';
        }), palette);
        const screenshot = await page.screenshot({ fullPage: true });
        if (link === 'href' && palette.name === 'accent') fs.writeFileSync(path.join(output, 'browser-checks.png'), screenshot);
        for (const card of positions) {
          const a = await sharp(screenshot).extract(cropBox(card.boxes[0])).ensureAlpha().raw().toBuffer();
          const b = await sharp(screenshot).extract(cropBox(card.boxes[1])).ensureAlpha().raw().toBuffer();
          let maxDelta = 0, offPalette = 0, inkPixels = 0;
          for (let i = 0; i < a.length; i += 4) {
            let ink = false;
            for (let channel = 0; channel < 3; channel++) {
              maxDelta = Math.max(maxDelta, Math.abs(a[i + channel] - b[i + channel]));
              const low = Math.min(palette.foreground[channel], palette.background[channel]) - 2;
              const high = Math.max(palette.foreground[channel], palette.background[channel]) + 2;
              if (b[i + channel] < low || b[i + channel] > high) offPalette++;
              if (Math.abs(b[i + channel] - palette.background[channel]) > 10) ink = true;
            }
            if (ink) inkPixels++;
          }
          results.push({ id: card.id, link, palette: palette.name, maxDelta, offPalette, inkPixels });
        }
      }
    }
    const image = await page.screenshot({ fullPage: true });
    const rotationBoxes = await page.evaluate(() => [...document.querySelectorAll('article[data-rotation]')].map(card => {
      const b = card.querySelector('.rotation').getBoundingClientRect();
      return { id: card.dataset.rotation, box: { x: b.x + scrollX, y: b.y + scrollY, width: b.width, height: b.height } };
    }));
    const rotationResults = [];
    for (const rotation of rotationBoxes) {
      const pixels = await sharp(image).extract(cropBox(rotation.box)).ensureAlpha().raw().toBuffer();
      let outsidePixels = 0;
      for (let y = 0; y < 128; y++) for (let x = 0; x < 128; x++) {
        if (x >= 16 && x < 112 && y >= 16 && y < 112) continue;
        const i = (y * 128 + x) * 4;
        if (pixels[i] < 247 || pixels[i + 1] < 247 || pixels[i + 2] < 247) outsidePixels++;
      }
      rotationResults.push({ id: rotation.id, outsidePixels });
    }
    const failures = results.filter(r => r.maxDelta > 80 || r.offPalette || r.inkPixels < 5);
    const rotationFailures = rotationResults.filter(r => r.outsidePixels);
    const summary = { icons: positions.length, comparisons: results.length, rotationChecks: rotationResults.length,
      failures, rotationFailures, sourceOverflows, errors, maxAntialiasDelta: Math.max(...results.map(r => r.maxDelta)) };
    fs.writeFileSync(path.join(output, 'browser-results.json'), JSON.stringify({ summary, results, rotations: rotationResults }, null, 2) + '\n');
    console.log(JSON.stringify(summary, null, 2));
    assert.deepEqual(errors, []); assert.deepEqual(failures, []); assert.deepEqual(rotationFailures, []); assert.deepEqual(sourceOverflows, []);
  } finally {
    if (browser) await browser.close();
    server.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
