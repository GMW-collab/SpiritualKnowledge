"""Shared helpers for source adapters. Standard library only."""
import json
import os
import re
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"
CONTENT = ROOT / "content"
UA = "HarkhowalOnline-updater/2.0 (+https://www.harkhowal.com; once-daily)"


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def today():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def load_config():
    return json.loads((ROOT / "config.json").read_text(encoding="utf-8"))


def load(name, default, base=None):
    try:
        return json.loads(((base or DATA) / name).read_text(encoding="utf-8"))
    except Exception:
        return default


def save(name, obj, compact=False, base=None):
    d = base or DATA
    d.mkdir(parents=True, exist_ok=True)
    txt = json.dumps(obj, ensure_ascii=False, separators=(",", ":")) if compact \
        else json.dumps(obj, ensure_ascii=False, indent=1)
    (d / name).write_text(txt + "\n", encoding="utf-8")


_SECRET_ENV = ("YOUTUBE_API_KEY", "FACEBOOK_PAGE_TOKEN")


def scrub(text):
    """Remove any secret values from a message before it is logged or saved."""
    text = str(text)
    for k in _SECRET_ENV:
        v = os.environ.get(k)
        if v:
            text = text.replace(v, "***")
    return re.sub(r"(key|token|access_token)=[^&\s]+", r"\1=***", text)


def request(url, method="GET", retries=2, timeout=30, delay=3, opener=None):
    """GET returns decoded text; HEAD returns headers. Retries with backoff."""
    last = None
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, method=method, headers={"User-Agent": UA})
            fn = opener or urllib.request.urlopen
            with fn(req, timeout=timeout) as r:
                if method == "HEAD":
                    return r.headers
                return r.read().decode("utf-8", errors="replace")
        except Exception as e:  # network, HTTP or decode error
            last = e
            if attempt < retries:
                time.sleep(delay * (attempt + 1))
    raise RuntimeError(scrub(last))


class SourceResult:
    """What an adapter reports back to the orchestrator."""

    def __init__(self, state, message="", counts=None):
        assert state in ("ok", "partial", "kept-previous", "failed", "not-configured", "needs-credentials", "disabled")
        self.state = state
        self.message = scrub(message)
        self.counts = counts or {}
