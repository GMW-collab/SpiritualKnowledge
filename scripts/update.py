#!/usr/bin/env python3
"""Daily content update.

Runs every source registered under "sources" in config.json through its
adapter (scripts/sources/<adapter>.py), and records what happened in
data/sync-status.json, which the Sources and Review pages display.

One source failing never affects another, and a source that cannot be
reached keeps its previous data, so a bad day never empties the website.

  python scripts/update.py            # all enabled sources
  python scripts/update.py youtube    # just one, by id
"""
import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from sources.common import SourceResult, load, load_config, now_iso, save  # noqa: E402

ADAPTERS = {"youtube": "youtube", "gurmatveechar": "gurmatveechar", "sheet": "sheet",
            "feed": "feeds", "banidb": "banidb"}


def run_source(cfg, src):
    if not src.get("enabled", True):
        return SourceResult("disabled", src.get("note", "Turned off in config.json"))
    adapter = src.get("adapter")
    if not adapter:  # registered for the record, no automated integration (e.g. needs credentials)
        return SourceResult(src.get("state", "needs-credentials"), src.get("note", ""))
    mod = importlib.import_module("sources." + ADAPTERS[adapter])
    try:
        return mod.run(cfg, src)
    except Exception as e:  # an adapter bug must not stop the others
        return SourceResult("failed", f"{type(e).__name__}: {e}")


def main(only=None):
    cfg = load_config()
    status = load("sync-status.json", {"sources": {}})
    prev = status.get("sources", {})
    out = {}
    for src in cfg.get("sources", []):
        sid = src["id"]
        if only and sid not in only:
            if sid in prev:
                out[sid] = prev[sid]
            continue
        res = run_source(cfg, src)
        p = prev.get(sid, {})
        entry = {
            "title": src.get("title", sid), "adapter": src.get("adapter"), "method": src.get("method", ""),
            "state": res.state, "message": res.message, "counts": res.counts or p.get("counts", {}),
            "last_attempt": now_iso(),
            "last_success": now_iso() if res.state in ("ok", "partial") else p.get("last_success", ""),
        }
        out[sid] = entry
        print(f"{sid:14} {res.state:16} {res.message}", file=sys.stderr if res.state not in ("ok", "not-configured", "disabled", "needs-credentials") else sys.stdout)
    save("sync-status.json", {"updated": now_iso(), "sources": out})
    return out


if __name__ == "__main__":
    main(set(sys.argv[1:]) or None)
