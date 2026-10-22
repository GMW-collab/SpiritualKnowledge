#!/usr/bin/env python3
"""Automated accessibility audit with axe-core (WCAG 2.1 A and AA rules).

  npm install axe-core@4.10.2
  python tests/a11y_check.py node_modules/axe-core/axe.min.js

Builds the site, serves it locally, blocks outside requests, and runs axe on a
representative page of every kind, in light and dark mode, at desktop and phone
widths. Fails on any 'serious' or 'critical' violation; lists the rest.
"""
import http.server
import json
import os
import socketserver
import sys
import tempfile
import threading
from functools import partial
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
os.environ["BASE_PATH"] = "/"
import build  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

AXE = Path(sys.argv[1] if len(sys.argv) > 1 else "node_modules/axe-core/axe.min.js")
PAGES = ["", "latest/", "topics/", "topics/sukhmani/", "journey/", "themes/haumai/", "listen/",
         "listen/vichar-sagar/", "watch/", "search/?q=gurmukh", "about/", "sources/", "no-such-page"]

out = Path(tempfile.mkdtemp()) / "site"
build.build(out)


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send_error(self, code, message=None, explain=None):
        if code == 404:
            body = (out / "404.html").read_bytes()
            self.send_response(404)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(body)
            return
        super().send_error(code, message, explain)


srv = socketserver.TCPServer(("127.0.0.1", 0), partial(Quiet, directory=str(out)))
URL = f"http://127.0.0.1:{srv.server_address[1]}/"
threading.Thread(target=srv.serve_forever, daemon=True).start()

serious, minor = [], []
with sync_playwright() as p:
    b = p.chromium.launch()
    for scheme in ("light", "dark"):
        for width in (1280, 390):
            pg = b.new_page(viewport={"width": width, "height": 900}, color_scheme=scheme)
            pg.route("**/*", lambda r: r.continue_() if r.request.url.startswith(URL) else r.abort())
            for path in PAGES:
                pg.goto(URL + path)
                pg.wait_for_load_state("networkidle")
                pg.add_script_tag(path=str(AXE))
                res = pg.evaluate("""async () => {
                    const r = await axe.run(document, {runOnly: {type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']}});
                    return r.violations.map(v => ({id: v.id, impact: v.impact, help: v.help,
                        nodes: v.nodes.slice(0, 3).map(n => n.target.join(' ') + ' :: ' + (n.failureSummary || '').split('\\n').slice(0, 2).join(' '))}));
                }""")
                for v in res:
                    key = f"[{scheme} {width}px] /{path} {v['id']} ({v['impact']}): {v['help']}"
                    (serious if v["impact"] in ("serious", "critical") else minor).append((key, v["nodes"]))
            pg.close()
    b.close()
srv.shutdown()

def annotate(level, group):
    """Group by rule and emit GitHub annotations, so results are readable from the checks API."""
    rules = {}
    for key, nodes in group:
        rule = key.split("] /", 1)[1].split(" ", 1)[1]
        where = key.split("] /", 1)[0] + "] /" + key.split("] /", 1)[1].split(" ", 1)[0]
        r = rules.setdefault(rule, {"where": [], "nodes": []})
        r["where"].append(where.strip("["))
        r["nodes"] += [n for n in nodes if n not in r["nodes"]]
    for rule, r in list(rules.items())[:10]:
        msg = f"{len(r['where'])} page views: {'; '.join(r['where'][:6])}%0A" + "%0A".join(n[:240] for n in r["nodes"][:4])
        print(f"::{level} title=axe {rule[:120]}::{msg}")


if os.environ.get("GITHUB_ACTIONS"):
    annotate("error", serious)
    annotate("warning", minor)

for title, group in (("Serious or critical", serious), ("Moderate or minor", minor)):
    print(f"\n{title}: {len(group)}")
    for key, nodes in group:
        print(" ", key)
        for n in nodes:
            print("     ", n[:220])
print(json.dumps({"serious": len(serious), "minor": len(minor)}))
sys.exit(1 if serious else 0)
