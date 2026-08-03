#!/usr/bin/env python3
"""Renders README.md through GitHub's own markdown API and wraps the result in a
GitHub-dark shell, so the profile can be reviewed at the real column width."""

import json
import pathlib
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent

SHELL = """<!doctype html><html lang="ru"><head><meta charset="utf-8">
<title>Profile README preview</title><style>
:root {{ color-scheme: dark; }}
body {{ margin:0; background:#010409; color:#e6edf3;
  font:16px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Noto Sans,Helvetica,Arial,sans-serif; }}
.page {{ max-width:1280px; margin:0 auto; padding:24px 16px 80px; display:grid;
  grid-template-columns:296px 1fr; gap:24px; }}
.side {{ border:1px solid #30363d; border-radius:6px; height:420px; background:#0d1117; }}
.card {{ border:1px solid #30363d; border-radius:6px; background:#0d1117; padding:32px 32px 40px; min-width:0; }}
.card img {{ max-width:100%; box-sizing:border-box; }}
.card h3 {{ margin:24px 0 16px; padding-bottom:.3em; font-size:1.25em; border-bottom:1px solid #3d444d; }}
.card p {{ margin:0 0 16px; }}
.card a {{ color:#4493f8; text-decoration:none; }}
.card details {{ margin:0 0 16px; }}
.card summary {{ cursor:pointer; }}
.card .anchor {{ display:none; }}
</style></head><body><div class="page"><div class="side"></div>
<div class="card">{body}</div></div></body></html>"""


def main():
    md = (ROOT / "README.md").read_text()
    req = urllib.request.Request(
        "https://api.github.com/markdown",
        data=json.dumps({"text": md, "mode": "markdown"}).encode(),
        headers={
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "User-Agent": "profile-preview",
        },
    )
    html = urllib.request.urlopen(req, timeout=25).read().decode()
    html = html.replace('src="assets/', 'src="../assets/')
    out = ROOT / "preview" / "readme.html"
    out.write_text(SHELL.format(body=html))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
