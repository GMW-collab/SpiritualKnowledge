#!/usr/bin/env python3
"""Make a self-contained preview of the site (relative links, every page an explicit index.html).

  python scripts/preview.py <out-dir>

The preview works from any folder or sub-path, including a sandboxed preview
frame that only serves the site's own files. In that frame, outside audio and
YouTube cannot load; the pages say so. Redirect stubs, the 404 page and the
sitemap are left out because they only make sense on the real domain.
"""
import os
import posixpath
import re
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ["BASE_PATH"] = "/"
import build  # noqa: E402

SKIP_DIRS = set(build.REDIRECTS)
ATTR = re.compile(r'\b(href|src|action|data-src)="(/[^"]*)"')


def rel(from_file, target):
    m = re.search(r"[?#]", target)
    path, rest = (target[:m.start()], target[m.start():]) if m else (target, "")
    sep = ""
    if path.endswith("/"):
        path += "index.html"
    r = posixpath.relpath(path.lstrip("/") or "index.html", posixpath.dirname(from_file) or ".")
    return r + sep + rest


def main(out):
    out = Path(out)
    tmp = Path(tempfile.mkdtemp()) / "site"
    build.build(tmp)
    if out.exists():
        shutil.rmtree(out)
    files = []
    for p in sorted(tmp.rglob("*")):
        relp = p.relative_to(tmp).as_posix()
        if p.is_dir() or relp.split("/")[0] in SKIP_DIRS or relp in ("404.html", "sitemap.xml", "robots.txt", ".nojekyll", "CNAME"):
            continue
        dest = out / relp
        dest.parent.mkdir(parents=True, exist_ok=True)
        if p.suffix == ".html":
            txt = p.read_text(encoding="utf-8")
            txt = ATTR.sub(lambda m: f'{m.group(1)}="{rel(relp, m.group(2))}"', txt)
            depth = relp.count("/")
            base = "../" * depth or "./"
            txt = re.sub(r'<body data-base="/"', f'<body data-base="{base}" data-rel="1" data-preview="1"', txt)
            if relp == "index.html":
                # The preview host wraps its main page in its own document; keep only head contents and body.
                txt = re.sub(r"^<!doctype html>\s*<html[^>]*>\s*<head>\s*", "", txt)
                txt = re.sub(r'<meta charset="utf-8">\s*<meta name="viewport"[^>]*>\s*', "", txt)
                txt = re.sub(r"</head>\s*<body ([^>]*)>", r'<div id="sitecfg" hidden \1></div>', txt)
                txt = re.sub(r"</body>\s*</html>\s*$", "", txt)
            dest.write_text(txt, encoding="utf-8")
        else:
            shutil.copy2(p, dest)
        files.append(relp)
    shutil.rmtree(tmp.parent)
    return files


if __name__ == "__main__":
    fs = main(sys.argv[1] if len(sys.argv) > 1 else "_preview")
    print(f"{len(fs)} files")
