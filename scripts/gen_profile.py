#!/usr/bin/env python3
"""Build the animated GitHub profile README: SVG pieces + README.md.
Inspired by github.com/basteez/basteez (Persona 5 aesthetic)

    python scripts/gen_profile.py

Inputs : profile.config.json (what to show; edit this)
         assets/profile.json  (stats & repo data)
Outputs: assets/stage/*.svg and README.md (generated, do not hand-edit)
"""
import datetime
import glob
import json
import math
import os
import random
import re
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = json.load(open(os.path.join(ROOT, "profile.config.json"), encoding="utf-8"))
DATA = json.load(open(os.path.join(ROOT, "assets", "profile.json"), encoding="utf-8"))
OUT_DIR = os.path.join(ROOT, "assets", "stage")
REL = "assets/stage"
W = 900

RED, BLACK, WHITE = "#e60012", "#000", "#fff"
MONO = "'JetBrains Mono','Fira Code','SF Mono',Menlo,Consolas,'DejaVu Sans Mono',monospace"
SANS = "'Arial Black','Helvetica Neue',Arial,sans-serif"
SERIF = "Georgia,'Times New Roman',serif"
COLLAGE_FONTS = [
    "Impact,'Arial Black',sans-serif",
    "Georgia,'Times New Roman',serif",
    "'Courier New',Courier,monospace",
    "'Arial Black',Arial,sans-serif",
    "'Trebuchet MS',Verdana,sans-serif",
]
TILE_SCHEMES = [(WHITE, BLACK), (RED, WHITE), (BLACK, WHITE), (WHITE, RED)]


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def fmt(n):
    return f"{n:,}"


def uid(*parts):
    return "u" + format(zlib.crc32("|".join(map(str, parts)).encode()), "x")


BASE_CSS = """
.pop{transform-box:fill-box;transform-origin:center;animation:pop .5s cubic-bezier(.2,1.7,.4,1) both}
@keyframes pop{0%{transform:scale(0) rotate(-40deg);opacity:0}60%{transform:scale(1.3) rotate(8deg);opacity:1}100%{transform:scale(1) rotate(0)}}
.wob{transform-box:fill-box;transform-origin:center;animation:wob 1.8s ease-in-out infinite alternate}
@keyframes wob{from{transform:rotate(-5deg) translateY(-2px)}to{transform:rotate(5deg) translateY(2px)}}
.slamL{animation:slamL .45s cubic-bezier(.2,1.4,.4,1) both}
@keyframes slamL{from{transform:translateX(-1100px)}to{transform:none}}
.slamR{animation:slamR .45s cubic-bezier(.2,1.4,.4,1) both}
@keyframes slamR{from{transform:translateX(1100px)}to{transform:none}}
.drop{transform-box:fill-box;transform-origin:center;animation:drop .5s cubic-bezier(.2,1.6,.4,1) both}
@keyframes drop{from{transform:translateY(-400px) rotate(-30deg);opacity:0}to{transform:none;opacity:1}}
.thump{transform-box:fill-box;transform-origin:center;animation:thump 1.2s ease-in-out infinite}
@keyframes thump{0%,100%{transform:scale(1)}12%{transform:scale(1.15)}24%{transform:scale(1)}}
.blink{animation:blink 1s steps(1) infinite}
@keyframes blink{50%{opacity:0}}
.marquee{animation:marquee linear infinite}
@keyframes marquee{to{transform:translateX(var(--d))}}
.type{transform-box:fill-box;transform-origin:0 50%;animation:type linear both}
@keyframes type{from{transform:scaleX(0)}to{transform:scaleX(1)}}
"""


def svg(w, h, title, body, css="", defs="", clip_round=None):
    clip = ""
    if clip_round is not None:
        defs += f'<clipPath id="frame"><rect width="{w}" height="{h}" rx="{clip_round}"/></clipPath>'
        body = f'<g clip-path="url(#frame)">{body}</g>'
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-label="{esc(title)}">'
        f"<title>{esc(title)}</title><style>{BASE_CSS}{css}</style>"
        f"<defs>{defs}</defs>{clip}{body}</svg>\n"
    )


def collage(text, x, y, size, rng, delay=0.0, step=0.06, schemes=TILE_SCHEMES, wobble=0.65, outline=False):
    """Ransom-note letters: each glyph its own cut-paper tile, font, tilt and pop-in."""
    out, cx = [], x
    for i, ch in enumerate(text):
        if ch == " ":
            cx += size * 0.4
            continue
        s = size * rng.uniform(0.82, 1.16)
        w, h = s * 0.8, s * 1.02
        bg, fg = rng.choice(schemes)
        font = rng.choice(COLLAGE_FONTS)
        rot, dy = rng.uniform(-10, 10), rng.uniform(-0.09, 0.09) * size
        glyph = ch.upper() if rng.random() < 0.72 or not ch.isalpha() else ch.lower()
        j = lambda: rng.uniform(-0.07, 0.07) * s  # ragged paper edges
        pts = f"{-w/2+j():.1f},{-h/2+j():.1f} {w/2+j():.1f},{-h/2+j():.1f} {w/2+j():.1f},{h/2+j():.1f} {-w/2+j():.1f},{h/2+j():.1f}"
        stroke = ' stroke="#000" stroke-width="2"' if outline else ""
        tile = (
            f'<polygon points="{pts}" fill="{bg}"{stroke}/>'
            f'<text y="{s*0.32:.1f}" font-size="{s*0.86:.1f}" fill="{fg}" font-family="{font}" font-weight="900" text-anchor="middle">{esc(glyph)}</text>'
        )
        if rng.random() < wobble:
            tile = f'<g class="wob" style="animation-delay:{-rng.uniform(0,2):.2f}s">{tile}</g>'
        out.append(
            f'<g transform="translate({cx+w/2:.1f},{y+dy:.1f}) rotate({rot:.1f})">'
            f'<g class="pop" style="animation-delay:{delay+i*step:.2f}s">{tile}</g></g>'
        )
        cx += w * 1.04
    return "".join(out)


def marquee(text, x, y, width, size, fill, speed=55):
    unit = text + "   ★   "
    tw = len(unit) * size * 0.6
    cid = uid("mq", text, x, y)
    return (
        f'<clipPath id="{cid}"><rect x="{x}" y="{y-size*1.2:.0f}" width="{width}" height="{size*1.8:.0f}"/></clipPath>'
        f'<g clip-path="url(#{cid})"><g class="marquee" style="--d:-{tw:.1f}px;animation-duration:{tw/speed:.1f}s" '
        f'font-family="{MONO}" font-size="{size}" font-weight="700" fill="{fill}">'
        + "".join(
            f'<text x="{x+k*tw:.1f}" y="{y}" textLength="{tw:.1f}" lengthAdjust="spacing" xml:space="preserve">{esc(unit)}</text>'
            for k in range(2 + int(width // tw))
        )
        + "</g></g>"
    )


def wrap(text, n):
    lines, cur = [], ""
    for w in text.split():
        if cur and len(cur) + 1 + len(w) > n:
            lines.append(cur)
            cur = w
        else:
            cur = (cur + " " + w).strip()
    return lines + ([cur] if cur else [])


STATS = DATA.get("stats", {"commits": 350, "stars": 15, "repos": 23, "followers": 12})


def targets():
    out = []
    for t in CFG.get("targets", []):
        r = DATA.get("repos", {}).get(t["repo"], {})
        out.append({
            "label": t.get("label") or t["repo"].upper(),
            "tag": (t.get("tag") or r.get("language") or "").upper(),
            "stars": r.get("stars", 0),
            "wip": t.get("wip", False),
            "url": t.get("url") or r.get("url") or f"https://github.com/vaibhav-24hr/{t['repo']}",
            "description": t.get("description") or r.get("description", "").strip(),
        })
    return out


# ------------------------------------------------------------------ pieces

def hero():
    rng = random.Random(42)
    H = 380
    css = """
.spin{transform-box:view-box;transform-origin:735px 190px;animation:spin 18s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
"""
    defs = '<pattern id="dots" width="10" height="10" patternUnits="userSpaceOnUse" patternTransform="rotate(30)"><circle cx="5" cy="5" r="2.1" fill="#000" fill-opacity=".28"/></pattern>'
    b = [f'<rect width="{W}" height="{H}" fill="{RED}"/>']
    rays = []
    for i in range(16):
        a0, a1 = math.radians(i * 22.5), math.radians(i * 22.5 + 11)
        rays.append(f"M735,190 L{735+900*math.cos(a0):.0f},{190+900*math.sin(a0):.0f} L{735+900*math.cos(a1):.0f},{190+900*math.sin(a1):.0f}Z")
    b.append(f'<path class="spin" d="{" ".join(rays)}" fill="#000" fill-opacity=".22"/>')
    b.append(f'<rect width="{W}" height="{H}" fill="url(#dots)"/>')
    b.append(
        '<g class="slamL">'
        '<polygon points="0,0 580,0 552,50 568,54 500,190 522,196 440,380 0,380" fill="#fff"/>'
        '<polygon points="0,0 560,0 532,46 548,50 482,186 502,192 422,380 0,380" fill="#000"/></g>'
    )
    first, last = CFG["name"]
    b.append(collage(first, 30, 92, 74, rng, delay=0.45))
    b.append(collage(last, 70, 186, 66, rng, delay=0.9, schemes=[(WHITE, BLACK), (RED, BLACK), (WHITE, RED), (RED, WHITE)]))
    role = CFG["role"]
    bw = len(role) * 15.5 + 40
    b.append(
        f'<g class="slamL" style="animation-delay:1.3s"><g transform="translate(34,244) skewX(-16)">'
        f'<rect width="{bw:.0f}" height="34" fill="#fff"/>'
        f'<text x="14" y="25" font-family="{SANS}" font-size="20" fill="#000" letter-spacing="1">{esc(role)}</text></g>'
        f'<text x="36" y="304" font-family="{MONO}" font-size="13" font-weight="700" fill="{RED}">{esc(" ▸ ".join(CFG["stack"]))}</text></g>'
    )
    b.append(
        f'<text x="36" y="350" font-family="{MONO}" font-size="11" fill="#fff" opacity=".7">SYS://FULLSTACK-AI ONLINE  ·  LOC: {esc(CFG["location"])}  ·  <tspan class="blink">█</tspan></text>'
    )
    cfg_stamps = CFG.get("stamps")
    if cfg_stamps and len(cfg_stamps) == 3:
        stamps = [
            (str(cfg_stamps[0]["value"]), cfg_stamps[0]["label"].upper(), 668, 92, -7, (WHITE, BLACK)),
            (str(cfg_stamps[1]["value"]), cfg_stamps[1]["label"].upper(), 806, 186, 6, (BLACK, WHITE)),
            (str(cfg_stamps[2]["value"]), cfg_stamps[2]["label"].upper(), 672, 286, -3, (WHITE, RED)),
        ]
    else:
        stamps = [
            (fmt(STATS["commits"]), "COMMITS", 668, 92, -7, (WHITE, BLACK)),
            (fmt(STATS["stars"]), "STARS", 806, 186, 6, (BLACK, WHITE)),
            (str(STATS["repos"]), "REPOS", 672, 286, -3, (WHITE, RED)),
        ]
    for i, (num, lbl, x, y, rot, (bg, fg)) in enumerate(stamps):
        fs = 32 if len(str(num)) > 4 else 40
        lbl_fs = 10 if len(lbl) > 8 else 12
        b.append(
            f'<g transform="translate({x},{y}) rotate({rot})"><g class="drop" style="animation-delay:{1.7+i*.2:.2f}s">'
            f'<polygon points="-70,-46 72,-52 66,44 -66,50" fill="#000" transform="translate(7,7)"/>'
            f'<polygon points="-70,-46 72,-52 66,44 -66,50" fill="{bg}"/>'
            f'<text y="10" font-family="{SANS}" font-size="{fs}" fill="{fg}" text-anchor="middle">{esc(str(num))}</text>'
            f'<text y="34" font-family="{MONO}" font-size="{lbl_fs}" font-weight="700" fill="{fg}" text-anchor="middle" letter-spacing="1.5">{esc(lbl)}</text></g></g>'
        )
    title = f"{first.title()} {last.title()} — {role.title()}. {fmt(STATS['commits'])} commits, {fmt(STATS['stars'])} stars, {STATS['repos']} public repos."
    return svg(W, H, title, "".join(b), css, defs, clip_round=14)


def about():
    lines = wrap(CFG["about"], 80)[:5]
    H = 70 + len(lines) * 26
    b = []
    pts = f"14,22 {W-10},8 {W-24},{H-10} 4,{H-4}"
    b.append(f'<g class="slamR"><polygon points="{pts}" fill="{RED}" transform="translate(8,6)"/>'
             f'<polygon points="{pts}" fill="#000" stroke="#fff" stroke-width="3"/></g>')
    b.append(
        f'<g class="drop" style="animation-delay:.35s"><g transform="translate(36,4) rotate(-4) skewX(-12)">'
        f'<rect width="150" height="34" fill="#fff" stroke="#000" stroke-width="2"/>'
        f'<text x="14" y="25" font-family="{SANS}" font-size="19" fill="#000">{esc(CFG["name"][0])}</text></g></g>'
    )
    t = 0.7
    for i, line in enumerate(lines):
        y = 62 + i * 26
        n, dur = len(line), len(line) * 0.018
        cid = uid("ab", i)
        b.append(
            f'<clipPath id="{cid}"><rect class="type" style="animation-delay:{t:.2f}s;animation-duration:{dur:.2f}s" x="40" y="{y-20}" width="{W-80}" height="28"/></clipPath>'
            f'<text clip-path="url(#{cid})" x="44" y="{y}" font-family="{SANS}" font-size="16" fill="#fff" font-weight="400">{esc(line)}</text>'
        )
        t += dur + 0.05
    b.append(f'<polygon class="blink" points="{W-60},{H-34} {W-44},{H-34} {W-52},{H-24}" fill="{RED}"/>')
    return svg(W, H, CFG["about"], "".join(b))


def section(title, seed):
    rng = random.Random(seed)
    H = 76
    b = [
        f'<g class="slamL"><polygon points="10,58 {W-40},40 {W-44},50 12,66" fill="{RED}"/></g>',
        collage(title, 20, 38, 40, rng, delay=0.1, step=0.04, wobble=0.2, outline=True),
    ]
    return svg(W, H, title, "".join(b))


def menu_item(i, n, t):
    H = 64
    cycle = n * 1.3
    a, z = 100 * i / n, 100 * (i + 1) / n
    on = f"{a+0.5:.1f}%,{z-0.5:.1f}%{{opacity:1;transform:none}}"
    off_before = f"0%,{a:.1f}%{{opacity:0;transform:translateX(-14px)}}" if i else ""
    off_after = f"{z:.1f}%,100%{{opacity:0;transform:translateX(-14px)}}" if i < n - 1 else ""
    kf = off_before + on + off_after
    if i == 0:
        kf = f"0%{{opacity:1;transform:none}}{z-0.5:.1f}%{{opacity:1;transform:none}}{z:.1f}%,100%{{opacity:0;transform:translateX(-14px)}}"
    css = f"""
.hl{{animation:hl {cycle:.1f}s steps(1) infinite}}
@keyframes hl{{{kf}}}
.menu{{animation:menu .4s cubic-bezier(.2,1.5,.4,1) both}}
@keyframes menu{{from{{transform:translate(950px,0)}}to{{transform:none}}}}
"""
    x = 64 + i * 16
    bw = 660
    status = f'<tspan class="blink" fill="{RED}">IN DEV ●</tspan>' if t["wip"] else (f"★ {t['stars']}" if t["stars"] else "")
    right = " · ".join(x for x in (esc(t["tag"]), status) if x)
    b = [
        f'<g class="menu" style="animation-delay:{.15+i*.1:.2f}s">',
        f'<g class="hl"><polygon points="{x-18},{6} {x+bw+30},{0} {x+bw+14},{H-4} {x-30},{H-2}" fill="#fff" stroke="#000" stroke-width="2"/>'
        f'<polygon points="{x-8},{11} {x+bw+18},{6} {x+bw+6},{H-9} {x-18},{H-7}" fill="{RED}"/>'
        f'<text x="{x-58}" y="{H/2+9}" font-family="{SANS}" font-size="26" fill="{RED}">▶</text></g>',
        f'<g transform="translate({x},14) skewX(-14)">'
        f'<rect x="6" y="5" width="{bw}" height="36" fill="{RED}"/>'
        f'<rect width="{bw}" height="36" fill="#000" stroke="#fff" stroke-width="2"/>'
        f'<text x="18" y="25" font-family="{SANS}" font-size="{18 if len(t["label"]) < 26 else 15}" fill="#fff">{esc(t["label"])}</text>'
        f'<text x="{bw-14}" y="24" font-family="{MONO}" font-size="12" font-weight="700" fill="#fff" text-anchor="end">{right}</text></g>',
        "</g>",
    ]
    title = f"{t['label']}: {t['description'] or t['tag']}" + (" (in development)" if t["wip"] else (f" — {t['stars']} stars" if t["stars"] else ""))
    return svg(W, H, title, "".join(b), css)


ICON_MAP = {
    "JAVA": "java",
    "PYTHON": "python",
    "TYPESCRIPT": "ts",
    "JAVASCRIPT": "js",
    "SQL": "postgres",
    "POSTGRES": "postgres",
    "MYSQL": "mysql",
    "REACT": "react",
    "NEXT.JS": "nextjs",
    "TAILWIND": "tailwind",
    "VITE": "vite",
    "REDUX": "redux",
    "NODE.JS": "nodejs",
    "EXPRESS": "express",
    "SPRING": "spring",
    "SPRING BOOT": "spring",
    "HIBERNATE": "hibernate",
    "MONGODB": "mongodb",
    "OPENAI": "openai",
    "GEMINI": "gemini",
    "MEDIAPIPE": "python",
    "AWS": "aws",
    "DOCKER": "docker",
    "FIREBASE": "firebase",
    "SUPABASE": "supabase",
    "GIT": "git",
    "LINUX": "linux",
}
ICONS_DIR = os.path.join(ROOT, "assets", "icons")


def get_icon_svg(icon_key, x, y, size=44):
    path = os.path.join(ICONS_DIR, f"{icon_key}.svg")
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    m = re.search(r'viewBox="([^"]+)"', content)
    vb = m.group(1) if m else "0 0 256 256"
    inner = re.sub(r"<\?xml[^>]*\?>", "", content)
    inner = re.sub(r"<svg[^>]*>", "", inner, count=1)
    inner = inner.rsplit("</svg>", 1)[0]
    prefix = f"ic_{icon_key}_"
    inner = re.sub(r'id="([^"]+)"', rf'id="{prefix}\1"', inner)
    inner = re.sub(r"url\(#([^)]+)\)", rf"url(#{prefix}\1)", inner)
    return f'<svg x="{x}" y="{y}" width="{size}" height="{size}" viewBox="{vb}">{inner}</svg>'


def skill_card(i, skill_group):
    """Animated Persona-5 style tech category card with official vector logos only."""
    H = 68
    cat = skill_group["category"]
    items = skill_group["items"]
    rot = [-1.0, 1.2, -0.8, 1.0][i % 4]
    b = [
        f'<g transform="rotate({rot} 450 {H/2:.0f})"><g class="drop" style="animation-delay:{.15+i*.12:.2f}s">',
        f'<polygon points="26,10 {W-26},6 {W-32},{H-6} 30,{H-4}" fill="{RED}" transform="translate(6,5)"/>',
        f'<polygon points="26,10 {W-26},6 {W-32},{H-6} 30,{H-4}" fill="#000" stroke="#fff" stroke-width="2.5"/>',
        f'<g transform="translate(44,14) skewX(-12)"><rect width="135" height="40" fill="#fff"/>'
        f'<text x="67" y="26" font-family="{SANS}" font-size="14" fill="#000" text-anchor="middle">{esc(cat)}</text></g>',
    ]
    icon_size = 44
    gap = 18
    by = int((H - icon_size) / 2)
    start_x = 210
    for idx, item in enumerate(items):
        bx = start_x + idx * (icon_size + gap)
        icon_key = ICON_MAP.get(item.upper(), "python")
        icon_svg_str = get_icon_svg(icon_key, bx, by, size=icon_size)
        delay = 0.25 + i * 0.1 + idx * 0.05
        b.append(
            f'<g class="pop" style="animation-delay:{delay:.2f}s">'
            f'<title>{esc(item)}</title>'
            f'<rect x="{bx+3}" y="{by+3}" width="{icon_size}" height="{icon_size}" rx="10" fill="{RED}"/>'
            f'{icon_svg_str}'
            f'</g>'
        )
    b.append("</g></g>")
    return svg(W, H, f"{cat}: {', '.join(items)}", "".join(b))


def contact(i, c):
    w, h = 190, 68
    rot = [-5, 4, -3, 5, -4, 3][i % 6]
    bg, fg = [(BLACK, WHITE), (WHITE, BLACK), (RED, WHITE), (WHITE, RED)][i % 4]
    sh = RED if bg != RED else BLACK
    label = c["label"]
    fs = 18 if len(label) <= 9 else 14
    b = [
        f'<g transform="rotate({rot} {w/2} {h/2})"><g class="pop" style="animation-delay:{.1+i*.1:.2f}s">',
        f'<polygon points="14,14 {w-10},10 {w-16},{h-12} 10,{h-10}" fill="{sh}" transform="translate(6,5)"/>',
        f'<polygon points="14,14 {w-10},10 {w-16},{h-12} 10,{h-10}" fill="{bg}" stroke="#000" stroke-width="2.5"/>',
        f'<text x="{w/2}" y="{h/2+fs*0.36:.1f}" font-family="{SANS}" font-size="{fs}" fill="{fg}" text-anchor="middle">{esc(label)}</text>',
        "</g></g>",
    ]
    return svg(w, h, label, "".join(b))


def ticker():
    H = 44
    text = (f"{fmt(STATS['commits'])} COMMITS   ★   {fmt(STATS['stars'])} STARS   ★   {STATS['repos']} PUBLIC REPOS   ★   "
            f"OPEN TO WORK: VANCOUVER & REMOTE   ★   TECH: FULLSTACK + AI INTEGRATIONS   ★   THANKS FOR VISITING")
    b = [
        f'<g transform="skewX(-14)"><rect x="20" y="6" width="{W-34}" height="32" fill="#000" stroke="{RED}" stroke-width="3"/></g>',
        marquee(text, 18, 28, W - 40, 13, "#fff", speed=60),
    ]
    return svg(W, H, text.title(), "".join(b))


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    for f in glob.glob(os.path.join(OUT_DIR, "*.svg")):
        try:
            os.remove(f)
        except OSError:
            pass

    def write(name, content):
        with open(os.path.join(OUT_DIR, name), "w", encoding="utf-8") as f:
            f.write(content)
        return f"{REL}/{name}"

    tg = targets()
    skills_data = CFG.get("skills", [])
    first, last = CFG["name"]

    md = [
        "<!--\n  GENERATED by scripts/gen_profile.py. Do not edit by hand.\n"
        "  To change what's shown, edit profile.config.json and run:\n"
        "      python scripts/gen_profile.py\n-->\n",
        f'<p align="center"><img src="{write("hero.svg", hero())}" width="100%" alt="{esc(first.title())} {esc(last.title())}, {esc(CFG["role"].title())}. {fmt(STATS["commits"])} commits, {fmt(STATS["stars"])} stars, {STATS["repos"]} public repos." /></p>\n',
        f'<p align="center"><img src="{write("about.svg", about())}" width="100%" alt="{esc(CFG["about"])}" /></p>\n',
        f'<p align="center"><img src="{write("h-targets.svg", section("SELECT TARGET", 1))}" width="100%" alt="Select target" /><br>',
    ]

    for i, t in enumerate(tg):
        alt = f"{t['label']}: {t['description'] or t['tag']}"
        md.append(f'<a href="{esc(t["url"])}"><img src="{write(f"target-{i}.svg", menu_item(i, len(tg), t))}" width="100%" alt="{esc(alt)}" /></a><br>')
    md.append("</p>\n")

    if skills_data:
        md.append(f'<p align="center"><img src="{write("h-skills.svg", section("TECH ARSENAL", 2))}" width="100%" alt="Tech Arsenal" /><br>')
        for i, sk in enumerate(skills_data):
            md.append(f'<img src="{write(f"skill-{i}.svg", skill_card(i, sk))}" width="100%" alt="{esc(sk["category"])}" /><br>')
        md.append("</p>\n")

    md.append(f'<p align="center"><img src="{write("h-contact.svg", section("CONTACT", 3))}" width="100%" alt="Contact" /><br>')
    for i, c in enumerate(CFG.get("contacts", [])):
        src = write(f"contact-{slug(c['label'])}.svg", contact(i, c))
        md.append(f'<a href="{esc(c["url"])}"><img src="{src}" height="46" alt="{esc(c["label"].title())}" /></a>')
    md.append("</p>\n")

    md.append(f'<p align="center"><img src="{write("ticker.svg", ticker())}" width="100%" alt="Stats ticker" /></p>\n')

    with open(os.path.join(ROOT, "README.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(md))

    count = len(glob.glob(os.path.join(OUT_DIR, "*.svg")))
    print(f"✅ Generated README.md + {count} SVGs in {REL}/")


if __name__ == "__main__":
    main()
