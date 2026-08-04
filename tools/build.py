#!/usr/bin/env python3
"""Builds every SVG asset for the cyberpunk GitHub profile.

    python tools/build.py            # everything
    python tools/build.py hero       # a single asset

Design language: chamfered HUD panels, one cyan accent, magenta only as a
chromatic-aberration channel. All motion collapses under prefers-reduced-motion.
"""

from __future__ import annotations

import sys

from kit import (
    ASSETS,
    CHAMFER,
    REDUCED_MOTION,
    T,
    chamfer,
    esc,
    icon_path,
    load_config,
    load_fonts,
    write_asset,
)

W = 1200
PAD = 64


# ---------------------------------------------------------------------------
# shared fragments
# ---------------------------------------------------------------------------
def defs_texture(w: int, h: int) -> str:
    """Scanlines, grain, vignette and CRT sweep. Purely atmospheric layers."""
    return f"""
  <pattern id="scan" width="1" height="4" patternUnits="userSpaceOnUse">
    <rect width="1" height="1" fill="#000" opacity=".45"/>
  </pattern>
  <linearGradient id="sweepG" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="{T['cy']}" stop-opacity="0"/>
    <stop offset=".5" stop-color="{T['cy']}" stop-opacity=".055"/>
    <stop offset="1" stop-color="{T['cy']}" stop-opacity="0"/>
  </linearGradient>
  <radialGradient id="vig" cx=".5" cy=".45" r=".78">
    <stop offset=".55" stop-color="#000" stop-opacity="0"/>
    <stop offset="1" stop-color="#000" stop-opacity=".55"/>
  </radialGradient>
  <filter id="grain" x="0" y="0" width="100%" height="100%">
    <feTurbulence type="fractalNoise" baseFrequency=".9" numOctaves="3" stitchTiles="stitch"/>
    <feColorMatrix type="saturate" values="0"/>
  </filter>
  <filter id="bloom" x="-40%" y="-40%" width="180%" height="180%">
    <feGaussianBlur stdDeviation="3.4" result="b"/>
    <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>"""


def texture_layer(w: int, h: int, sweep: bool = True) -> str:
    sweep_el = (
        f'\n    <rect class="sweep" x="0" y="{-h}" width="{w}" height="{h}" fill="url(#sweepG)"/>'
        if sweep
        else ""
    )
    return f"""
    <rect class="scan" x="0" y="-6" width="{w}" height="{h + 12}" fill="url(#scan)" opacity=".2"/>{sweep_el}
    <rect x="0" y="0" width="{w}" height="{h}" filter="url(#grain)" opacity=".05" style="mix-blend-mode:overlay"/>
    <rect x="0" y="0" width="{w}" height="{h}" fill="url(#vig)"/>"""


def texture_css() -> str:
    return """
.scan { animation: drift 9s linear infinite; }
@keyframes drift { to { transform: translateY(4px); } }
.sweep { animation: sweep 8.5s cubic-bezier(.55,0,.45,1) infinite; }
"""


def frame(w: int, h: int, cham: int = CHAMFER + 6) -> tuple[str, str]:
    """Returns (clip-path def, stroked frame + corner brackets)."""
    d = chamfer(0.5, 0.5, w - 1, h - 1, cham, "tl,br")
    b = 20
    brackets = (
        f'<path d="M{w - 1 - b},1.5 H{w - 1.5} V{1 + b}" fill="none" stroke="{T["cy"]}" '
        f'stroke-width="1.5" opacity=".85"/>'
        f'<path d="M1.5,{h - 1 - b} V{h - 1.5} H{1 + b}" fill="none" stroke="{T["cy"]}" '
        f'stroke-width="1.5" opacity=".85"/>'
        f'<path d="M0.5,{cham} L{cham},0.5" fill="none" stroke="{T["cy"]}" stroke-width="1.5" opacity=".55"/>'
        f'<path d="M{w - cham},{h - 0.5} L{w - 0.5},{h - cham}" fill="none" stroke="{T["cy"]}" '
        f'stroke-width="1.5" opacity=".55"/>'
    )
    return (
        f'<clipPath id="frame"><path d="{chamfer(0, 0, w, h, cham, "tl,br")}"/></clipPath>',
        f'<path d="{d}" fill="none" stroke="{T["line2"]}" stroke-width="1"/>{brackets}',
    )


ENTER_CSS = """
.e { animation: enter .85s cubic-bezier(.16,1,.3,1) backwards; }
@keyframes enter { from { opacity:0; transform: translateY(12px); } to { opacity:1; transform: translateY(0); } }
"""


# ---------------------------------------------------------------------------
# HERO
# ---------------------------------------------------------------------------
def build_hero(cfg, fonts) -> str:
    H = 440
    ident = cfg["identity"]
    wordmark = ident["wordmark"].upper()
    handle = "@" + ident["handle"]
    roles = ident["roles"]
    stmt = ident["statement"]

    disp = fonts["display"].load(wordmark)
    mono = fonts["mono"].load(handle + stmt + "".join(roles) + "> " + "ONLINE")

    gap = disp.covers(wordmark)
    if gap:
        raise SystemExit(
            f"'{fonts['display'].family}' has no glyph for {''.join(gap)}.\n"
            f"  For a Cyrillic wordmark set fonts.display in profile.json to one of:\n"
            f'  {{"query": "Unbounded:wght@800", "family": "Unbounded", "weight": 800}}\n'
            f'  {{"query": "Tektur:wght@700", "family": "Tektur", "weight": 700}}\n'
            f'  {{"query": "Golos+Text:wght@800", "family": "Golos Text", "weight": 800}}'
        )

    # --- wordmark: fills the column left of the emblem, capped so short names
    #     do not turn into a poster and long names stay on one line
    EMB_X, EMB_Y, EMB_R = 1068, 172, 56
    wm_max = EMB_X - EMB_R - 104 - PAD
    wm_track = -0.015
    wm_size = disp.fit(wordmark, wm_max, 148, wm_track)
    wm_y = 216

    # --- typed role line
    role_size = 32
    cw = mono.width("M", role_size)  # monospace advance
    role_y = 286
    prefix_w = cw * 2
    type_x = PAD + prefix_w

    seg = []
    t = 0.0
    for r in roles:
        n = len(r)
        type_d, hold, del_d, gap = n * 0.062, 1.9, n * 0.03, 0.32
        seg.append((t, t + type_d, t + type_d + hold, t + type_d + hold + del_d, n))
        t += type_d + hold + del_d + gap
    total = t

    def pc(x):
        return round(x / total * 100, 3)

    type_css, type_svg = [], []
    for i, (s, t1, t2, t3, n) in enumerate(seg):
        full = round(n * cw, 2)
        head = "" if s == 0 else f"  0%,{pc(s)}% {{ width:0px; animation-timing-function: steps({n},end); }}\n"
        if s == 0:
            head = f"  0% {{ width:0px; animation-timing-function: steps({n},end); }}\n"
        type_css.append(
            f"@keyframes tw{i} {{\n{head}"
            f"  {pc(t1)}% {{ width:{full}px; }}\n"
            f"  {pc(t2)}% {{ width:{full}px; animation-timing-function: steps({n},end); }}\n"
            f"  {pc(t3)}%,100% {{ width:0px; }}\n}}\n"
            f"@keyframes cm{i} {{\n{head.replace('width:0px', 'transform:translateX(0px)')}"
            f"  {pc(t1)}% {{ transform:translateX({full}px); }}\n"
            f"  {pc(t2)}% {{ transform:translateX({full}px); animation-timing-function: steps({n},end); }}\n"
            f"  {pc(t3)}%,100% {{ transform:translateX(0px); }}\n}}\n"
            f"@keyframes cs{i} {{ 0%,{pc(max(s - 0.05, 0))}% {{ opacity:0; }} "
            f"{pc(s)}%,{pc(t3 + 0.28)}% {{ opacity:1; }} {pc(t3 + 0.3)}%,100% {{ opacity:0; }} }}\n"
            f".tr{i} {{ animation: tw{i} {total:.2f}s infinite; }}\n"
            f".cm{i} {{ animation: cm{i} {total:.2f}s infinite, blink 1.05s steps(1,end) infinite; }}\n"
            f".cs{i} {{ animation: cs{i} {total:.2f}s steps(1,end) infinite; }}\n"
        )
        type_svg.append(
            f'    <clipPath id="tc{i}"><rect class="tr{i}" x="{type_x}" y="{role_y - 26}" '
            f'width="{round(seg[i][4] * cw, 2) if i == 0 else 0}" height="36"/></clipPath>'
        )

    roles_svg = "\n".join(
        f'      <g clip-path="url(#tc{i})"><text class="role" x="{type_x}" y="{role_y}">{esc(r)}</text></g>\n'
        f'      <g class="cs{i}" opacity="{1 if i == 0 else 0}"><rect class="cur cm{i}" x="{type_x + 1}" y="{role_y - 20}" '
        f'width="{round(cw * .66, 2)}" height="26"/></g>'
        for i, (r, _) in enumerate(zip(roles, seg))
    )

    # --- statement
    stmt_size = 22
    while mono.width(stmt, stmt_size) > W - PAD * 2 and stmt_size > 12:
        stmt_size -= 0.5

    # --- perspective grid below the horizon
    HZ, GH, VPX = 352, H - 352, 900
    v_lines = "".join(
        f'<line x1="{VPX}" y1="{HZ}" x2="{VPX + (1 if k > 0 else -1) * k * k * 9}" y2="{HZ + GH}"/>'
        for k in range(-17, 18)
        if k != 0
    )
    h_lines = "".join(
        f'<line class="hz" style="animation-delay:{-i * 7 / 13:.2f}s" x1="0" y1="{HZ}" x2="{W}" y2="{HZ}"/>'
        for i in range(13)
    )

    handle_w = mono.width(handle, 20, 20 * 0.22)
    rail_x = PAD + 22 + handle_w + 22

    css = f"""
{fonts['display'].face_css()}
{fonts['mono'].face_css()}
text {{ font-family:'{fonts['mono'].family}',ui-monospace,monospace; fill:{T['text']}; }}
.wm {{ font-family:'{fonts['display'].family}',system-ui,sans-serif; font-weight:800; font-stretch:125%;
      font-size:{wm_size}px; letter-spacing:{wm_track}em; }}
.handle {{ font-size:20px; letter-spacing:.22em; fill:{T['text2']}; }}
.role {{ font-size:{role_size}px; fill:{T['text']}; }}
.chev {{ font-size:{role_size}px; fill:{T['cy']}; }}
.stmt {{ font-size:{stmt_size}px; fill:#8496AC; letter-spacing:.01em; }}
.cur {{ fill:{T['cy']}; }}
@keyframes blink {{ 0%,49% {{ opacity:1; }} 50%,100% {{ opacity:0; }} }}

{ENTER_CSS}
.e1 {{ animation-delay:.05s; }} .e2 {{ animation-delay:.15s; }} .e3 {{ animation-delay:.32s; }}
.e4 {{ animation-delay:.44s; }} .e5 {{ animation-delay:.2s; }} .e6 {{ animation-delay:.55s; }}

{texture_css()}
@keyframes sweep {{ 0% {{ transform:translateY(0); }} 62%,100% {{ transform:translateY({H * 2 + 40}px); }} }}

/* chromatic aberration: two offset channels + two torn bands, in short bursts */
.gc, .gm, .gs1, .gs2 {{ animation-timing-function: steps(1,end); animation-iteration-count:infinite;
  animation-duration:8s; }}
.gc {{ animation-name:gc; mix-blend-mode:screen; fill:{T['cy']}; }}
.gm {{ animation-name:gm; mix-blend-mode:screen; fill:{T['mg']}; }}
.gs1 {{ animation-name:gs1; }} .gs2 {{ animation-name:gs2; }}
@keyframes gc {{
  0%,2.9% {{ opacity:0; transform:translate(0,0); }}
  3% {{ opacity:.9; transform:translate(-7px,2px); }}
  3.7% {{ opacity:.9; transform:translate(5px,-3px); }}
  4.4%,40.9% {{ opacity:0; transform:translate(0,0); }}
  41% {{ opacity:.85; transform:translate(8px,-2px); }}
  41.8%,73.9% {{ opacity:0; transform:translate(0,0); }}
  74% {{ opacity:.9; transform:translate(-5px,-2px); }}
  74.9% {{ opacity:.9; transform:translate(4px,2px); }}
  75.6%,100% {{ opacity:0; transform:translate(0,0); }}
}}
@keyframes gm {{
  0%,2.9% {{ opacity:0; transform:translate(0,0); }}
  3% {{ opacity:.8; transform:translate(7px,-2px); }}
  3.7% {{ opacity:.8; transform:translate(-5px,3px); }}
  4.4%,40.9% {{ opacity:0; transform:translate(0,0); }}
  41% {{ opacity:.75; transform:translate(-8px,2px); }}
  41.8%,73.9% {{ opacity:0; transform:translate(0,0); }}
  74% {{ opacity:.8; transform:translate(5px,2px); }}
  74.9% {{ opacity:.8; transform:translate(-4px,-2px); }}
  75.6%,100% {{ opacity:0; transform:translate(0,0); }}
}}
@keyframes gs1 {{
  0%,2.9% {{ opacity:0; transform:translate(0,0); }}
  3%,3.6% {{ opacity:1; transform:translate(18px,0); }}
  3.7%,40.9% {{ opacity:0; transform:translate(0,0); }}
  41%,41.7% {{ opacity:1; transform:translate(-14px,0); }}
  41.8%,73.9% {{ opacity:0; transform:translate(0,0); }}
  74%,74.8% {{ opacity:1; transform:translate(11px,0); }}
  74.9%,100% {{ opacity:0; transform:translate(0,0); }}
}}
@keyframes gs2 {{
  0%,3.2% {{ opacity:0; transform:translate(0,0); }}
  3.3%,4% {{ opacity:1; transform:translate(-22px,0); }}
  4.1%,41.2% {{ opacity:0; transform:translate(0,0); }}
  41.3%,42% {{ opacity:1; transform:translate(16px,0); }}
  42.1%,74.2% {{ opacity:0; transform:translate(0,0); }}
  74.3%,75.1% {{ opacity:1; transform:translate(-13px,0); }}
  75.2%,100% {{ opacity:0; transform:translate(0,0); }}
}}

/* horizon: a data packet running along the rail */
.pkt {{ stroke-dasharray:130 942; animation: pkt 5.5s linear infinite; }}
@keyframes pkt {{ from {{ stroke-dashoffset:1072; }} to {{ stroke-dashoffset:0; }} }}
.rail {{ transform-origin:{PAD}px 0; animation: rail 1.1s cubic-bezier(.16,1,.3,1) .5s backwards; }}
@keyframes rail {{ from {{ transform:scaleX(0); }} to {{ transform:scaleX(1); }} }}

/* grid receding toward the horizon */
.hz {{ stroke:{T['cy']}; stroke-width:1; opacity:.45; animation: hz 7s linear infinite; }}
@keyframes hz {{
  0% {{ transform:translateY(0); opacity:0; }}
  14% {{ opacity:.75; }}
  25% {{ transform:translateY({GH * .0625}px); }}
  50% {{ transform:translateY({GH * .25}px); }}
  75% {{ transform:translateY({GH * .5625}px); }}
  100% {{ transform:translateY({GH}px); opacity:.75; }}
}}

/* emblem: rotating HUD rings signal that the banner is live */
.r1 {{ animation: spin 34s linear infinite; }}
.r2 {{ animation: spin 9s linear infinite reverse; }}
.r3 {{ animation: spin 15s linear infinite; }}
.wedge {{ animation: spin 5.5s linear infinite; }}
.core {{ animation: core 3.4s ease-in-out infinite; }}
@keyframes spin {{ to {{ transform:rotate(360deg); }} }}
@keyframes core {{ 0%,100% {{ opacity:.35; }} 50% {{ opacity:1; }} }}

{"".join(type_css)}
{REDUCED_MOTION}
@media (prefers-reduced-motion: reduce) {{
  .tr0 {{ width: {round(seg[0][4] * cw, 2)}px !important; }}
  .cs0 {{ opacity: 1 !important; }}
  .cm0 {{ transform: translateX({round(seg[0][4] * cw, 2)}px) !important; }}
  {" ".join(f".cs{i} {{ opacity: 0 !important; }}" for i in range(1, len(seg)))}
}}
"""

    clip_def, frame_svg = frame(W, H)

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img"
     aria-label="{esc(ident['wordmark'])} - {esc(', '.join(roles))}. {esc(stmt)}">
  <title>{esc(ident['wordmark'])} - {esc(' / '.join(roles))}</title>
  <defs>
    <style><![CDATA[{css}]]></style>
    {clip_def}
    <radialGradient id="glowA" cx=".08" cy="1" r=".95">
      <stop offset="0" stop-color="{T['cy']}" stop-opacity=".24"/>
      <stop offset="1" stop-color="{T['cy']}" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="glowB" cx=".93" cy=".06" r=".52">
      <stop offset="0" stop-color="{T['mg']}" stop-opacity=".07"/>
      <stop offset="1" stop-color="{T['mg']}" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="glowT">
      <stop offset="0" stop-color="{T['cy']}" stop-opacity=".075"/>
      <stop offset="1" stop-color="{T['cy']}" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="gridV" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#fff" stop-opacity=".04"/>
      <stop offset=".45" stop-color="#fff" stop-opacity=".9"/>
      <stop offset="1" stop-color="#fff" stop-opacity=".55"/>
    </linearGradient>
    <linearGradient id="gridH" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#fff" stop-opacity=".05"/>
      <stop offset=".42" stop-color="#fff" stop-opacity=".3"/>
      <stop offset="1" stop-color="#fff" stop-opacity="1"/>
    </linearGradient>
    <mask id="mV"><rect x="0" y="{HZ}" width="{W}" height="{GH}" fill="url(#gridV)"/></mask>
    <mask id="mH"><rect x="0" y="{HZ}" width="{W}" height="{GH}" fill="url(#gridH)"/></mask>
    <linearGradient id="wedgeG" x1="0" y1="1" x2="1" y2="0">
      <stop offset="0" stop-color="{T['cy']}" stop-opacity=".2"/>
      <stop offset="1" stop-color="{T['cy']}" stop-opacity="0"/>
    </linearGradient>
    <clipPath id="band1"><rect x="0" y="{wm_y - wm_size * .62}" width="{W}" height="{wm_size * .17}"/></clipPath>
    <clipPath id="band2"><rect x="0" y="{wm_y - wm_size * .3}" width="{W}" height="{wm_size * .14}"/></clipPath>
{chr(10).join(type_svg)}
{defs_texture(W, H)}
  </defs>

  <g clip-path="url(#frame)">
    <rect width="{W}" height="{H}" fill="{T['bg']}"/>
    <rect width="{W}" height="{H}" fill="url(#glowA)"/>
    <rect width="{W}" height="{H}" fill="url(#glowB)"/>
    <ellipse cx="{PAD + 340}" cy="{wm_y - 32}" rx="560" ry="160" fill="url(#glowT)"/>

    <g class="e e5">
      <g mask="url(#mV)"><g mask="url(#mH)">
        <g stroke="{T['cy']}" stroke-width="1" opacity=".5" fill="none">{v_lines}</g>
        <g opacity=".9" fill="none">{h_lines}</g>
      </g></g>
      <line class="rail" x1="{PAD}" y1="{HZ}" x2="{W - PAD}" y2="{HZ}" stroke="{T['line2']}" stroke-width="1"/>
      <line class="pkt" x1="{PAD}" y1="{HZ}" x2="{W - PAD}" y2="{HZ}" stroke="{T['cy']}" stroke-width="1.6"
            filter="url(#bloom)"/>
    </g>

    <g class="e e1">
      <path d="{chamfer(PAD, 80, 12, 12, 4, 'tl,br')}" fill="{T['cy']}"/>
      <text class="handle" x="{PAD + 26}" y="{93}">{esc(handle)}</text>
      <line x1="{rail_x}" y1="{86.5}" x2="{W - PAD}" y2="{86.5}" stroke="{T['line']}" stroke-width="1"
            class="rail" style="transform-origin:{rail_x}px 0"/>
    </g>

    <g class="e e2">
      <text class="wm gm" x="{PAD}" y="{wm_y}">{esc(wordmark)}</text>
      <text class="wm gc" x="{PAD}" y="{wm_y}">{esc(wordmark)}</text>
      <text class="wm" x="{PAD}" y="{wm_y}">{esc(wordmark)}</text>
      <g clip-path="url(#band1)" class="gs1"><text class="wm" x="{PAD}" y="{wm_y}">{esc(wordmark)}</text></g>
      <g clip-path="url(#band2)" class="gs2"><text class="wm" x="{PAD}" y="{wm_y}">{esc(wordmark)}</text></g>
    </g>

    <g class="e e3">
      <text class="chev" x="{PAD}" y="{role_y}">&gt;</text>
{roles_svg}
    </g>

    <g class="e e4">
      <text class="stmt" x="{PAD}" y="{role_y + 42}">{esc(stmt)}</text>
    </g>

    <g class="e e6"><g transform="translate({EMB_X},{EMB_Y})">
      <path d="{chamfer(-EMB_R - 10, -EMB_R - 10, (EMB_R + 10) * 2, (EMB_R + 10) * 2, 18, 'tl,br')}"
            fill="none" stroke="{T['line2']}" stroke-width="1"/>
      <path class="wedge" d="M0,0 L0,-{EMB_R} A{EMB_R},{EMB_R} 0 0 1 {EMB_R * .71},-{EMB_R * .71} Z"
            fill="url(#wedgeG)"/>
      <circle class="r1" r="{EMB_R}" fill="none" stroke="{T['line2']}" stroke-width="1" stroke-dasharray="2 9"/>
      <circle class="r2" r="{EMB_R - 13}" fill="none" stroke="{T['cy']}" stroke-width="1.6"
              stroke-dasharray="46 224" opacity=".95" filter="url(#bloom)"/>
      <circle class="r3" r="{EMB_R - 25}" fill="none" stroke="{T['cyDim']}" stroke-width="1" stroke-dasharray="9 7"/>
      <path class="core" d="{chamfer(-11, -11, 22, 22, 6, 'tl,br')}" fill="{T['cy']}" fill-opacity=".16"
            stroke="{T['cy']}" stroke-width="1.2"/>
    </g></g>
{texture_layer(W, H)}
  </g>
  {frame_svg}
</svg>"""
    return svg


# ---------------------------------------------------------------------------
# STACK MATRIX
# ---------------------------------------------------------------------------
def build_stack(cfg, fonts) -> str:
    rows = cfg["stack"]
    cell, gap = 96, 24
    cols = max(len(r["icons"]) for r in rows)
    grid_x = 320
    grid_w = cols * cell + (cols - 1) * gap
    H = PAD + len(rows) * cell + (len(rows) - 1) * gap + PAD
    labels = "".join(r["label"].upper() for r in rows)
    mono = fonts["mono"].load(labels + "ABCDEFGHIJKLMNOPQRSTUVWXYZ /")

    missing, cells, tint, symbols = [], [], [], []
    for ri, row in enumerate(rows):
        y = PAD + ri * (cell + gap)
        cells.append(
            f'    <text class="cat" x="{PAD}" y="{y + cell / 2 + 5}">{esc(row["label"].upper())}</text>'
        )
        for ci, slug in enumerate(row["icons"]):
            x = grid_x + ci * (cell + gap)
            got = icon_path(slug)
            if not got:
                missing.append(slug)
                continue
            d, title = got
            idx = ri * cols + ci
            # each mark is defined once and referenced twice: base layer + scan tint
            symbols.append(
                f'    <g id="i{idx}" transform="translate({x + cell / 2 - 20},{y + cell / 2 - 20}) '
                f'scale({40 / 24})"><path d="{d}"/></g>'
            )
            box = chamfer(x, y, cell, cell, 12, "tl,br")
            cells.append(
                f'    <g class="cell" style="animation-delay:{.25 + idx * .022:.3f}s">'
                f'<path d="{box}" fill="{T["bg2"]}" stroke="{T["line"]}" stroke-width="1"/>'
                f'<use href="#i{idx}" fill="{T["text2"]}" opacity=".92"><title>{esc(title)}</title></use></g>'
            )
            tint.append(
                f'    <g fill="{T["cy"]}"><path d="{box}" fill="none" stroke="{T["cy"]}" '
                f'stroke-width="1.4"/><use href="#i{idx}" fill="{T["cy"]}"/></g>'
            )
    if missing:
        print("  ! Simple Icons slugs not found:", ", ".join(missing))

    css = f"""
{fonts['mono'].face_css()}
text {{ font-family:'{fonts['mono'].family}',ui-monospace,monospace; }}
.cat {{ font-size:22px; letter-spacing:.2em; fill:{T['dim']}; }}
.cell {{ animation: pop .6s cubic-bezier(.16,1,.3,1) backwards; }}
@keyframes pop {{ from {{ opacity:0; transform:translateY(10px); }} to {{ opacity:1; transform:translateY(0); }} }}
/* a light bar sweeps the matrix and re-lights every cell it crosses */
.scanpass {{ animation: pass 7s cubic-bezier(.65,0,.35,1) 1.2s infinite; }}
@media (prefers-reduced-motion: reduce) {{ .scanpass {{ opacity:0 !important; }} }}
@keyframes pass {{ 0% {{ transform:translateX(-{grid_w + 460}px); }} 55%,100% {{ transform:translateX({grid_w + 300}px); }} }}
{texture_css()}
@keyframes sweep {{ 0% {{ transform:translateY(0); }} 62%,100% {{ transform:translateY({H * 2 + 40}px); }} }}
{REDUCED_MOTION}
"""
    clip_def, frame_svg = frame(W, H)
    alt = "; ".join(f'{r["label"]}: {", ".join(r["icons"])}' for r in rows)

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img"
     aria-label="Technology stack. {esc(alt)}">
  <title>Stack matrix</title>
  <defs>
    <style><![CDATA[{css}]]></style>
    {clip_def}
    <linearGradient id="passG" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#fff" stop-opacity="0"/>
      <stop offset=".42" stop-color="#fff" stop-opacity=".85"/>
      <stop offset=".5" stop-color="#fff" stop-opacity="1"/>
      <stop offset=".58" stop-color="#fff" stop-opacity=".85"/>
      <stop offset="1" stop-color="#fff" stop-opacity="0"/>
    </linearGradient>
    <mask id="passM">
      <rect class="scanpass" x="{grid_x - 240}" y="0" width="480" height="{H}" fill="url(#passG)"/>
    </mask>
    <radialGradient id="glowS" cx=".78" cy="0" r=".9">
      <stop offset="0" stop-color="{T['cy']}" stop-opacity=".09"/>
      <stop offset="1" stop-color="{T['cy']}" stop-opacity="0"/>
    </radialGradient>
{defs_texture(W, H)}
{chr(10).join(symbols)}
  </defs>
  <g clip-path="url(#frame)">
    <rect width="{W}" height="{H}" fill="{T['panel']}"/>
    <rect width="{W}" height="{H}" fill="url(#glowS)"/>
{chr(10).join(cells)}
    <g mask="url(#passM)" style="mix-blend-mode:screen">
{chr(10).join(tint)}
    </g>
{texture_layer(W, H)}
  </g>
  {frame_svg}
</svg>"""


# ---------------------------------------------------------------------------
# CAPABILITIES
# ---------------------------------------------------------------------------
def build_capabilities(cfg, fonts) -> str:
    cols = cfg["capabilities"]
    n = len(cols)
    gutter = 32
    col_w = (W - PAD * 2 - gutter * (n - 1)) / n
    text_all = "".join(c["title"] + "".join(c["items"]) for c in cols)
    mono = fonts["mono"].load(text_all)
    disp = fonts["monoBold"].load("".join(c["title"] for c in cols))

    lead, sub_lead = 48, 30
    text_w = col_w - 26
    # one type size for the whole panel: shrink until the longest item fits on a
    # single line, and only fall back to wrapping past the legibility floor
    title_track = 0.16
    title_size = min(
        26, min(disp.fit(c["title"].upper(), col_w, 26, title_track) for c in cols)
    )
    item_size = max(
        18.0,
        min(24.0, min(text_w / (mono.width(i, 1.0) or 1) for c in cols for i in c["items"])),
    )

    def wrap(s: str) -> list[str]:
        words, lines, cur = s.split(), [], ""
        for w in words:
            probe = f"{cur} {w}".strip()
            if mono.width(probe, item_size) <= text_w or not cur:
                cur = probe
            else:
                lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
        return lines

    wrapped = [[wrap(i) for i in c["items"]] for c in cols]
    col_h = [
        sum(lead + (len(l) - 1) * sub_lead for l in col) for col in wrapped
    ]
    H = 148 + max(col_h) + 14

    body = []
    for i, col in enumerate(cols):
        x = PAD + i * (col_w + gutter)
        body.append(
            f'    <g class="e" style="animation-delay:{.1 + i * .12:.2f}s">'
            f'<line class="rule" x1="{x}" y1="62" x2="{x + col_w}" y2="62" stroke="{T["line2"]}" stroke-width="1" '
            f'style="transform-origin:{x}px 0"/>'
            f'<line class="rule" x1="{x}" y1="62" x2="{x + 54}" y2="62" stroke="{T["cy"]}" stroke-width="2" '
            f'style="transform-origin:{x}px 0"/>'
            f'<text class="ct" x="{x}" y="102">{esc(col["title"].upper())}</text>'
        )
        y = 148
        for j, lines in enumerate(wrapped[i]):
            spans = "".join(
                f'<tspan x="{x + 26}" dy="{0 if k == 0 else sub_lead}">{esc(ln)}</tspan>'
                for k, ln in enumerate(lines)
            )
            body.append(
                f'<g class="e" style="animation-delay:{.2 + i * .12 + j * .05:.2f}s">'
                f'<path d="{chamfer(x + 1, y - 11, 10, 10, 3.5, "tl,br")}" fill="{T["cy"]}" opacity=".85"/>'
                f'<text class="it" y="{y}">{spans}</text></g>'
            )
            y += lead + (len(lines) - 1) * sub_lead
        body.append("</g>")

    css = f"""
{fonts['mono'].face_css()}
{fonts['monoBold'].face_css()}
text {{ font-family:'{fonts['mono'].family}',ui-monospace,monospace; }}
.ct {{ font-size:{title_size}px; font-weight:700; letter-spacing:{title_track}em; fill:{T['text']}; }}
.it {{ font-size:{item_size:.1f}px; fill:{T['text2']}; letter-spacing:.005em; }}
{ENTER_CSS}
.rule {{ animation: rule .9s cubic-bezier(.16,1,.3,1) .25s backwards; }}
@keyframes rule {{ from {{ transform:scaleX(0); }} to {{ transform:scaleX(1); }} }}
{texture_css()}
@keyframes sweep {{ 0% {{ transform:translateY(0); }} 62%,100% {{ transform:translateY({H * 2 + 40}px); }} }}
{REDUCED_MOTION}
"""
    clip_def, frame_svg = frame(W, int(H))
    alt = " | ".join(f'{c["title"]}: {"; ".join(c["items"])}' for c in cols)

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {int(H)}" width="{W}" height="{int(H)}"
     role="img" aria-label="{esc(alt)}">
  <title>Capabilities</title>
  <defs>
    <style><![CDATA[{css}]]></style>
    {clip_def}
    <radialGradient id="glowC" cx=".12" cy="1" r=".9">
      <stop offset="0" stop-color="{T['cy']}" stop-opacity=".08"/>
      <stop offset="1" stop-color="{T['cy']}" stop-opacity="0"/>
    </radialGradient>
{defs_texture(W, int(H))}
  </defs>
  <g clip-path="url(#frame)">
    <rect width="{W}" height="{int(H)}" fill="{T['panel']}"/>
    <rect width="{W}" height="{int(H)}" fill="url(#glowC)"/>
{chr(10).join(body)}
{texture_layer(W, int(H))}
  </g>
  {frame_svg}
</svg>"""


# ---------------------------------------------------------------------------
# STATS  (self-hosted: the public github-readme-stats instance is unreliable)
# ---------------------------------------------------------------------------
# label plural, label singular, read(user, own_repos, cfg)
METRICS = {
    "repos": (
        "REPOSITORIES",
        "REPOSITORY",
        lambda u, r, c: u.get("owned_repos", u.get("public_repos", 0)),
    ),
    "stars": ("STARS EARNED", "STAR EARNED", lambda u, r, c: sum(x.get("stargazers_count", 0) for x in r)),
    "followers": ("FOLLOWERS", "FOLLOWER", lambda u, r, c: u.get("followers", 0)),
    "following": ("FOLLOWING", "FOLLOWING", lambda u, r, c: u.get("following", 0)),
    "years": ("YEARS ON GITHUB", "YEAR ON GITHUB", lambda u, r, c: _years(u.get("created_at", ""))),
    "forks": ("FORKS", "FORK", lambda u, r, c: sum(x.get("forks_count", 0) for x in r)),
    "industries": ("INDUSTRIES SERVED", "INDUSTRY SERVED", lambda u, r, c: len(_industries(c))),
}


def _industries(cfg) -> list[str]:
    return [s for s in cfg.get("stats", {}).get("industries", []) if s.strip()]


def _years(iso: str) -> int:
    from datetime import datetime, timezone

    if not iso:
        return 0
    born = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    return max(0, int((datetime.now(timezone.utc) - born).days // 365.25))


def _owned_repo_count(login: str, token: str) -> int | None:
    import json
    import urllib.error
    import urllib.request

    query = """
    query($login: String!) {
      user(login: $login) {
        repositories(first: 1, ownerAffiliations: OWNER) {
          totalCount
        }
      }
    }
    """
    body = json.dumps({"query": query, "variables": {"login": login}}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "profile-builder",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            payload = json.loads(r.read())
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return None
    if payload.get("errors"):
        return None
    user = (payload.get("data") or {}).get("user")
    if not user:
        return None
    repos = user.get("repositories") or {}
    count = repos.get("totalCount")
    return count if isinstance(count, int) else None


def gh_stats(login: str, wanted: list[str], cfg: dict) -> dict:
    import json
    import os
    import urllib.error
    import urllib.request

    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    head = {"Accept": "application/vnd.github+json", "User-Agent": "profile-builder"}
    if token:
        head["Authorization"] = f"Bearer {token}"

    def api(path):
        req = urllib.request.Request("https://api.github.com" + path, headers=head)
        with urllib.request.urlopen(req, timeout=25) as r:
            return json.loads(r.read())

    user = api(f"/users/{login}")
    owned = _owned_repo_count(login, token) if token else None
    if owned is None:
        owned = cfg.get("stats", {}).get("repo_count")
    if owned is None:
        owned = user.get("public_repos", 0)
    user["owned_repos"] = owned

    repos, page = [], 1
    while page <= 4:
        chunk = api(f"/users/{login}/repos?per_page=100&type=owner&page={page}")
        repos += chunk
        if len(chunk) < 100:
            break
        page += 1

    own = [r for r in repos if not r.get("fork")]
    langs: dict[str, int] = {}
    for r in own:
        if r.get("language"):
            langs[r["language"]] = langs.get(r["language"], 0) + 1
    top = sorted(langs.items(), key=lambda kv: -kv[1])[:5]
    total = sum(c for _, c in top) or 1
    metrics = []
    for key in wanted:
        if key not in METRICS:
            continue
        plural, singular, read = METRICS[key]
        value = read(user, own, cfg)
        metrics.append((singular if value == 1 else plural, value))
    return {"metrics": metrics, "langs": [(name, c / total) for name, c in top]}


def _short(n: int) -> str:
    if n >= 10000:
        return f"{n / 1000:.0f}k"
    if n >= 1000:
        return f"{n / 1000:.1f}k".replace(".0k", "k")
    return str(n)


def build_stats(cfg, fonts) -> str:
    login = cfg["identity"]["handle"]
    conf = cfg.get("stats", {})
    wanted = conf.get("metrics", ["repos", "stars", "followers"])
    data = gh_stats(login, wanted, cfg)

    # The lower half is one slot: industry chips win over the language bar,
    # because a hand-kept domain list survives private work and the API one does not.
    tags = [s.upper() for s in _industries(cfg)]
    show_langs = not tags and conf.get("languages", True) and bool(data["langs"])

    values = [_short(v) for _, v in data["metrics"]]
    labels = [l for l, _ in data["metrics"]]
    n_col = max(len(values), 1)
    disp = fonts["display"].load("".join(values) + "0123456789k")
    mono = fonts["mono"].load(
        "".join(labels) + "".join(tags) + "".join(n for n, _ in data["langs"])
        + "TOP LANGUAGES BY REPOSITORYINDUSTE0123456789%"
    )

    # metric labels sit on baseline 158, so the divider clears them at 186
    CHIP_H, CHIP_GAP, CHIP_PAD, TAG_SIZE, TAG_TRACK, CHIP_TOP = 38, 10, 18, 19, 2.3, 240
    rows_of_chips: list[list[tuple[str, float]]] = []
    if tags:
        chips_w = [(t, mono.width(t, TAG_SIZE, TAG_TRACK) + CHIP_PAD * 2) for t in tags]
        full = W - PAD * 2

        def wrap(limit):
            rows, row, used = [], [], 0.0
            for tag, cw in chips_w:
                if row and used + CHIP_GAP + cw > limit:
                    rows.append(row)
                    row, used = [], 0.0
                used += (CHIP_GAP if row else 0) + cw
                row.append((tag, cw))
            return rows + ([row] if row else [])

        # Greedy filling strands the last row. Squeeze the wrap width down to the
        # narrowest that still needs the same number of rows: the rows even out.
        rows_of_chips = wrap(full)
        lo, hi = max(w for _, w in chips_w), full
        while lo <= hi:
            mid = (lo + hi) // 2
            trial = wrap(mid)
            if len(trial) <= len(rows_of_chips):
                rows_of_chips, hi = trial, mid - 1
            else:
                lo = mid + 1

    if tags:
        n_rows = len(rows_of_chips)
        H = CHIP_TOP + n_rows * CHIP_H + (n_rows - 1) * CHIP_GAP + 44
    else:
        H = 350 if show_langs else 210

    body, col_w = [], (W - PAD * 2) / n_col
    for i, ((label, _), value) in enumerate(zip(data["metrics"], values)):
        x = PAD + i * col_w
        body.append(
            f'    <g class="e" style="animation-delay:{.1 + i * .1:.2f}s">'
            f'<text class="num" x="{x}" y="122">{esc(value)}</text>'
            f'<text class="lbl" x="{x + 3}" y="158">{esc(label)}</text></g>'
        )

    bar_y, bar_h, bar_w = 252, 18, W - PAD * 2
    x, seg, legend = PAD, [], []
    for i, (name, frac) in enumerate(data["langs"] if show_langs else []):
        w = max(bar_w * frac, 3)
        op = [1, .74, .54, .38, .26][min(i, 4)]
        seg.append(
            f'    <rect class="seg" x="{x:.1f}" y="{bar_y}" width="{w - 2:.1f}" height="{bar_h}" '
            f'fill="{T["cy"]}" opacity="{op}" style="transform-origin:{x:.1f}px 0;'
            f'animation-delay:{.35 + i * .09:.2f}s"/>'
        )
        legend.append((name, frac, op))
        x += w
    lx, leg = PAD, []
    for i, (name, frac, op) in enumerate(legend):
        leg.append(
            f'    <g class="e" style="animation-delay:{.5 + i * .07:.2f}s">'
            f'<rect x="{lx}" y="{bar_y + 46}" width="11" height="11" fill="{T["cy"]}" opacity="{op}"/>'
            f'<text class="leg" x="{lx + 21}" y="{bar_y + 57}">{esc(name)} {frac * 100:.0f}%</text></g>'
        )
        lx += mono.width(f"{name} {frac * 100:.0f}%", 19) + 58

    css = f"""
{fonts['display'].face_css()}
{fonts['mono'].face_css()}
text {{ font-family:'{fonts['mono'].family}',ui-monospace,monospace; }}
.num {{ font-family:'{fonts['display'].family}',system-ui,sans-serif; font-weight:800; font-stretch:125%;
  font-size:74px; letter-spacing:-.02em; fill:{T['text']}; }}
.lbl {{ font-size:19px; letter-spacing:.2em; fill:{T['dim']}; }}
.cap {{ font-size:19px; letter-spacing:.2em; fill:{T['dim']}; }}
.leg {{ font-size:19px; fill:{T['text2']}; }}
.tag {{ font-size:{TAG_SIZE}px; letter-spacing:{TAG_TRACK / TAG_SIZE:.3f}em; fill:{T['text2']}; }}
{ENTER_CSS}
.seg {{ animation: grow .95s cubic-bezier(.16,1,.3,1) backwards; }}
@keyframes grow {{ from {{ transform:scaleX(0); }} to {{ transform:scaleX(1); }} }}
{texture_css()}
@keyframes sweep {{ 0% {{ transform:translateY(0); }} 62%,100% {{ transform:translateY({H * 2 + 40}px); }} }}
{REDUCED_MOTION}
@media (prefers-reduced-motion: reduce) {{ .seg {{ transform:none !important; }} }}
"""
    clip_def, frame_svg = frame(W, H)
    alt = ", ".join(f"{l.lower()} {v}" for (l, _), v in zip(data["metrics"], values))
    if tags:
        alt += ". Domains: " + ", ".join(t.lower() for t in tags)
    if show_langs:
        lang_block = (
            f'    <line x1="{PAD}" y1="{bar_y - 58}" x2="{W - PAD}" y2="{bar_y - 58}" '
            f'stroke="{T["line"]}" stroke-width="1"/>\n'
            f'    <text class="cap" x="{PAD}" y="{bar_y - 24}">TOP LANGUAGES BY REPOSITORY</text>\n'
            + "\n".join(seg + leg)
        )
    elif tags:
        chips, y, n = [], CHIP_TOP, 0
        for row in rows_of_chips:
            x = PAD
            for tag, cw in row:
                chips.append(
                    f'    <g class="e" style="animation-delay:{.34 + n * .035:.2f}s">'
                    f'<path d="{chamfer(x, y, cw, CHIP_H, 9, "tl,br")}" fill="{T["bg2"]}" '
                    f'stroke="{T["line"]}" stroke-width="1"/>'
                    f'<text class="tag" x="{x + CHIP_PAD}" y="{y + CHIP_H / 2 + 6.5:.1f}">{esc(tag)}</text></g>'
                )
                x += cw + CHIP_GAP
                n += 1
            y += CHIP_H + CHIP_GAP
        lang_block = (
            f'    <line x1="{PAD}" y1="{CHIP_TOP - 54}" x2="{W - PAD}" y2="{CHIP_TOP - 54}" '
            f'stroke="{T["line"]}" stroke-width="1"/>\n'
            f'    <text class="cap" x="{PAD}" y="{CHIP_TOP - 20}">DOMAINS SHIPPED IN</text>\n'
            + "\n".join(chips)
        )
    else:
        lang_block = ""

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img"
     aria-label="GitHub statistics for {esc(login)}: {esc(alt)}">
  <title>GitHub statistics</title>
  <defs>
    <style><![CDATA[{css}]]></style>
    {clip_def}
    <radialGradient id="glowM" cx=".2" cy=".1" r=".8">
      <stop offset="0" stop-color="{T['cy']}" stop-opacity=".1"/>
      <stop offset="1" stop-color="{T['cy']}" stop-opacity="0"/>
    </radialGradient>
{defs_texture(W, H)}
  </defs>
  <g clip-path="url(#frame)">
    <rect width="{W}" height="{H}" fill="{T['panel']}"/>
    <rect width="{W}" height="{H}" fill="url(#glowM)"/>
{chr(10).join(body)}
{lang_block}
{texture_layer(W, H)}
  </g>
  {frame_svg}
</svg>"""


# ---------------------------------------------------------------------------
# LINK BUTTONS
# ---------------------------------------------------------------------------
def build_buttons(cfg, fonts) -> list[str]:
    bw, bh = 300, 68
    mono = fonts["monoBold"].load("".join(l["label"].upper() for l in cfg["links"]))
    out = []
    for link in cfg["links"]:
        label = link["label"].upper()
        got = icon_path(link["icon"])
        d = got[0] if got else None
        if not got:
            print(f"  ! icon '{link['icon']}' not found, using a chamfer mark")
        size = 19
        while mono.width(label, size, size * 0.14) > bw - 116 and size > 12:
            size -= 0.5
        css = f"""
{fonts['monoBold'].face_css()}
text {{ font-family:'{fonts['monoBold'].family}',ui-monospace,monospace; font-weight:700;
  font-size:{size}px; letter-spacing:.14em; fill:{T['text']}; }}
.gl {{ opacity:.7; animation: gl 4.5s ease-in-out infinite; }}
@keyframes gl {{ 0%,100% {{ opacity:.25; }} 50% {{ opacity:.9; }} }}
.ic {{ fill:{T['cy']}; animation: ic 4.5s ease-in-out infinite; }}
@keyframes ic {{ 0%,100% {{ fill:{T['text2']}; }} 50% {{ fill:{T['cy']}; }} }}
{REDUCED_MOTION}
"""
        icon_svg = (
            f'<g class="ic" transform="translate(28,{bh / 2 - 11}) scale({22 / 24})"><path d="{d}"/></g>'
            if d
            else f'<path d="{chamfer(28, bh / 2 - 11, 22, 22, 6, "tl,br")}" fill="{T["cy"]}"/>'
        )
        svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {bw} {bh}" width="{bw}" height="{bh}"
     role="img" aria-label="{esc(link['label'])}">
  <title>{esc(link['label'])}</title>
  <defs><style><![CDATA[{css}]]></style>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="{T['bg2']}"/><stop offset="1" stop-color="{T['bg']}"/>
    </linearGradient>
  </defs>
  <path d="{chamfer(1, 1, bw - 2, bh - 2, 14, 'tl,br')}" fill="url(#bg)" stroke="{T['line2']}" stroke-width="1.5"/>
  <path class="gl" d="M1,15 L15,1" stroke="{T['cy']}" stroke-width="2" fill="none"/>
  <path class="gl" d="M{bw - 15},{bh - 1} L{bw - 1},{bh - 15}" stroke="{T['cy']}" stroke-width="2" fill="none"/>
  {icon_svg}
  <text x="66" y="{bh / 2 + 7}">{esc(label)}</text>
</svg>"""
        name = f"btn-{link['icon']}.svg"
        write_asset(name, svg)
        out.append(name)
    return out


def sync_readme_links(cfg) -> None:
    """Keep the README contact row in sync with profile.json links."""
    readme = ASSETS.parent / "README.md"
    start, end = "<!-- links:start -->", "<!-- links:end -->"
    text = readme.read_text(encoding="utf-8")
    if start not in text or end not in text:
        print(f"  ! README has no {start} / {end} markers, links not synced")
        return
    rows = "\n".join(
        f'<a href="{esc(l["url"])}"><img src="assets/btn-{l["icon"]}.svg" '
        f'alt="{esc(l["label"])}" width="182"></a>'
        for l in cfg["links"]
    )
    head, _, rest = text.partition(start)
    _, _, tail = rest.partition(end)
    readme.write_text(f"{head}{start}\n{rows}\n{end}{tail}", encoding="utf-8")
    print(f"  README contact row synced ({len(cfg['links'])} links)")


# ---------------------------------------------------------------------------
def main():
    cfg = load_config()
    fonts = load_fonts(cfg)
    want = sys.argv[1:] or ["hero", "stack", "capabilities", "buttons", "stats"]

    if "hero" in want:
        print("> hero.svg")
        write_asset("hero.svg", build_hero(cfg, fonts))
    if "stack" in want:
        print("> stack.svg")
        write_asset("stack.svg", build_stack(cfg, fonts))
    if "capabilities" in want:
        print("> capabilities.svg")
        write_asset("capabilities.svg", build_capabilities(cfg, fonts))
    if "buttons" in want:
        print("> buttons")
        build_buttons(cfg, fonts)
        sync_readme_links(cfg)
    if "stats" in want:
        print("> stats.svg")
        try:
            write_asset("stats.svg", build_stats(cfg, fonts))
        except Exception as e:
            print(f"  ! stats skipped ({e}). Set a real handle in profile.json, "
                  f"or GH_TOKEN if you are rate limited.")

    for f in sorted(ASSETS.glob("*.svg")):
        print(f"  {f.name:24} {f.stat().st_size / 1024:6.1f} KB")


if __name__ == "__main__":
    main()
