"""Writes an HTML page that renders every ```mermaid block of the given Markdown files, as written and with its
direction flipped (TB <-> LR), and reports each one's size. Serve the folder and open the page in a browser:

    uv run python scripts/architecture/render_check.py docs/ARCHITECTURE.md docs/EXTENDING.md --out build/render
    uv run python -m http.server 8765 --directory build/render

window.renderResults then lists {title, ok, error, asIs: [w, h], flipped: [w, h]} per diagram.
build.py's DIRECTIONS table records which direction to use where the flipped one is closer to 4:3.
"""

import argparse
import json
import re
from pathlib import Path

PAGE = """<!doctype html><html><head><meta charset="utf-8"><title>render check</title>
<script src="https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.min.js"></script>
<style>body{font-family:sans-serif;margin:16px} .err{color:#c92a2a;white-space:pre-wrap} h3{margin-top:32px}</style>
</head><body><h2 id="summary">checking…</h2><div id="out"></div>
<script>
const blocks = __BLOCKS__;
mermaid.initialize({startOnLoad:false, securityLevel:'strict', maxTextSize: 200000, maxEdges: 2000});
function flip(code) {
  if (/^\\s*classDiagram/.test(code)) {
    return /direction\\s+LR/.test(code) ? code.replace(/direction\\s+LR/, 'direction TB')
         : /direction\\s+(TB|TD|BT)/.test(code) ? code.replace(/direction\\s+(TB|TD|BT)/, 'direction LR')
         : code.replace('classDiagram', 'classDiagram\\n    direction LR');
  }
  const m = code.match(/^\\s*(?:%%\\{.*\\}%%\\s*)?flowchart\\s+(TB|TD|BT|LR|RL)/);
  if (m) return code.replace(m[0], m[0].replace(m[1], ['LR', 'RL'].includes(m[1]) ? 'TB' : 'LR'));
  return null;
}
async function size(id, code) {
  const { svg } = await mermaid.render(id, code);
  const vb = (svg.match(/viewBox="([^"]+)"/) || [,'0 0 0 0'])[1].split(' ').map(Number);
  return { svg, w: Math.round(vb[2]), h: Math.round(vb[3]) };
}
(async () => {
  const out = document.getElementById('out'); const results = [];
  for (let i = 0; i < blocks.length; i++) {
    const b = blocks[i]; const h = document.createElement('h3'); h.textContent = b.file + ' · ' + b.title;
    out.appendChild(h); const div = document.createElement('div'); out.appendChild(div);
    const r = { i, title: b.title, ok: true };
    try {
      const a = await size('a' + i, b.code); div.innerHTML = a.svg; r.asIs = [a.w, a.h];
      const f = flip(b.code); if (f) { const fl = await size('f' + i, f); r.flipped = [fl.w, fl.h]; }
    } catch (e) { r.ok = false; r.error = String(e && e.message || e).slice(0, 400);
      const p = document.createElement('pre'); p.className = 'err'; p.textContent = r.error; div.appendChild(p); }
    results.push(r);
  }
  window.renderResults = results;
  document.getElementById('summary').textContent = results.filter(r => r.ok).length + ' of ' + results.length + ' rendered';
})();
</script></body></html>"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("files", nargs="+")
    parser.add_argument("--out", default="build/render")
    args = parser.parse_args()
    blocks = []
    for f in args.files:
        text = Path(f).read_text(encoding="utf-8")
        for i, m in enumerate(re.finditer(r"```mermaid\n(.*?)```", text, re.S)):
            headings = re.findall(r"^#{2,3} (.+)$", text[:m.start()], re.M)
            blocks.append({"file": Path(f).name, "title": headings[-1] if headings else f"block {i}",
                           "code": m.group(1)})
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(PAGE.replace("__BLOCKS__", json.dumps(blocks)), encoding="utf-8")
    print(f"{len(blocks)} diagrams -> {out / 'index.html'}")


if __name__ == "__main__":
    main()
