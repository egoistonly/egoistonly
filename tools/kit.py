"""Shared toolkit for the cyberpunk profile assets: design tokens, font
subsetting/measuring, chamfered geometry and Simple Icons lookup.

Fonts must be inlined as base64 data URIs: GitHub serves README SVGs with
`default-src 'none'`, so any external @font-face or <image href> is blocked.
"""

from __future__ import annotations

import base64
import hashlib
import json
import re
import urllib.parse
import urllib.request
from io import BytesIO
from pathlib import Path

from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
CACHE = ROOT / "tools" / ".cache"

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

# --------------------------------------------------------------------------
# Design tokens. One accent (cyan). Magenta appears only as a chromatic
# aberration channel inside glitch bursts, never as a standalone accent.
# --------------------------------------------------------------------------
T = {
    "bg": "#05070C",
    "bg2": "#080C14",
    "panel": "#080B12",
    "line": "#16202E",
    "line2": "#223044",
    "text": "#E8F0FA",
    "text2": "#AFBFD3",
    "dim": "#66788F",
    "cy": "#00E5FF",
    "cyDim": "#0E7A8C",
    "mg": "#FF2E97",
}

CHAMFER = 14  # single corner-radius system for every asset: 14px chamfer, no rounding


def fetch(url: str, headers: dict | None = None) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def cached(key: str, producer) -> bytes:
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / key
    if path.exists():
        return path.read_bytes()
    data = producer()
    path.write_bytes(data)
    return data


# --------------------------------------------------------------------------
# Fonts
# --------------------------------------------------------------------------
class WebFont:
    """A Google font subsetted to exactly the glyphs an asset uses."""

    def __init__(self, spec: dict):
        self.query = spec["query"]
        self.family = spec["family"]
        self.weight = spec.get("weight", 400)
        self.stretch = spec.get("stretch")
        self._loaded: dict[str, tuple[bytes, TTFont]] = {}

    def _subset(self, text: str) -> tuple[bytes, TTFont]:
        chars = "".join(sorted(set(text) | set(" ")))
        key = hashlib.md5(f"{self.query}|{chars}".encode()).hexdigest()[:16]
        blob = cached(
            f"font-{key}.woff2",
            lambda: self._download(chars),
        )
        return blob, TTFont(BytesIO(blob))

    def _download(self, chars: str) -> bytes:
        css_url = (
            "https://fonts.googleapis.com/css2?family="
            + self.query
            + "&text="
            + urllib.parse.quote(chars, safe="")
            + "&display=swap"
        )
        css = fetch(css_url).decode()
        m = re.search(r"src:\s*url\((https://[^)]+)\)\s*format\('woff2'\)", css)
        if not m:
            raise RuntimeError(f"no woff2 in Google CSS for {self.query}:\n{css[:400]}")
        return fetch(m.group(1))

    def load(self, text: str):
        key = "".join(sorted(set(text)))
        if key not in self._loaded:
            self._loaded[key] = self._subset(text)
        self._blob, self._tt = self._loaded[key]
        self._upm = self._tt["head"].unitsPerEm
        self._cmap = self._tt.getBestCmap()
        self._hmtx = self._tt["hmtx"]
        return self

    def face_css(self) -> str:
        b64 = base64.b64encode(self._blob).decode()
        stretch = f"\n  font-stretch: {self.stretch};" if self.stretch else ""
        return (
            "@font-face {\n"
            f"  font-family: '{self.family}';\n"
            "  font-style: normal;\n"
            f"  font-weight: {self.weight};{stretch}\n"
            f"  src: url(data:font/woff2;charset=utf-8;base64,{b64}) format('woff2');\n"
            "}"
        )

    def advance(self, ch: str) -> float:
        name = self._cmap.get(ord(ch))
        if name is None:
            name = self._cmap.get(ord(" "))
        return self._hmtx[name][0] if name else 0.0

    def covers(self, text: str) -> list[str]:
        """Characters this font has no glyph for. Google serves a subset per
        request, so an uncovered script silently renders as fallback boxes."""
        return [c for c in dict.fromkeys(text) if c != " " and ord(c) not in self._cmap]

    def width(self, text: str, size: float, tracking: float = 0.0) -> float:
        """Ink width in px. `tracking` is extra px between glyphs."""
        if not text:
            return 0.0
        base = sum(self.advance(c) for c in text) / self._upm * size
        return base + tracking * (len(text) - 1)

    def fit(self, text: str, max_w: float, start: float, tracking_em: float = 0.0) -> float:
        """Largest font size (<= start) whose ink width fits max_w."""
        size = start
        while size > 8:
            if self.width(text, size, tracking_em * size) <= max_w:
                return size
            size -= 0.5
        return size


def load_fonts(cfg: dict) -> dict[str, WebFont]:
    return {k: WebFont(v) for k, v in cfg["fonts"].items()}


# --------------------------------------------------------------------------
# Geometry: chamfered rectangles are the single shape language of the system.
# --------------------------------------------------------------------------
def chamfer(x, y, w, h, c=CHAMFER, corners="tl,br") -> str:
    cs = {s.strip() for s in corners.split(",")}
    tl, tr, br, bl = ("tl" in cs, "tr" in cs, "br" in cs, "bl" in cs)
    p = []
    p.append(f"M{x + (c if tl else 0)},{y}")
    p.append(f"H{x + w - (c if tr else 0)}")
    if tr:
        p.append(f"L{x + w},{y + c}")
    p.append(f"V{y + h - (c if br else 0)}")
    if br:
        p.append(f"L{x + w - c},{y + h}")
    p.append(f"H{x + (c if bl else 0)}")
    if bl:
        p.append(f"L{x},{y + h - c}")
    p.append(f"V{y + (c if tl else 0)}")
    if tl:
        p.append(f"L{x + c},{y}")
    p.append("Z")
    return "".join(p)


def esc(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


# --------------------------------------------------------------------------
# Simple Icons: real brand marks, inlined as paths (external refs are blocked).
# --------------------------------------------------------------------------
_ICON_SRC = "https://cdn.jsdelivr.net/npm/simple-icons@latest/icons/{slug}.svg"


def icon_path(slug: str) -> tuple[str, str] | None:
    try:
        raw = cached(f"icon-{slug}.svg", lambda: fetch(_ICON_SRC.format(slug=slug))).decode()
    except Exception:
        return None
    d = re.search(r'<path[^>]*\sd="([^"]+)"', raw)
    title = re.search(r"<title>(.*?)</title>", raw)
    if not d:
        return None
    return d.group(1), (title.group(1) if title else slug)


def load_config() -> dict:
    return json.loads((ROOT / "profile.json").read_text())


def write_asset(name: str, svg: str) -> Path:
    ASSETS.mkdir(parents=True, exist_ok=True)
    path = ASSETS / name
    path.write_text(svg.strip() + "\n")
    return path


# Killing the animations is not enough: anything that starts at opacity 0 and
# relies on `forwards` would stay invisible, so every animated element also gets
# an explicit resting state here.
REDUCED_MOTION = """
@media (prefers-reduced-motion: reduce) {
  * { animation: none !important; transition: none !important; }
  .e, .cell { opacity: 1 !important; transform: none !important; }
  .hz { opacity: .45 !important; }
  .gc, .gm, .gs1, .gs2 { opacity: 0 !important; }
}
"""
