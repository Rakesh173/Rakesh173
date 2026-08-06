"""Build assets/spec-card.svg from live GitHub data.

Runs in Actions on a schedule. Talks to the GraphQL API once, then writes a
self contained SVG: no external fonts, no scripts, no runtime dependencies.
"""

import json
import os
import pathlib
import urllib.request
from datetime import datetime, timezone

LOGIN = os.environ.get("GH_LOGIN", "Rakesh173")
TOKEN = os.environ["GITHUB_TOKEN"]

QUERY = """
query($login: String!) {
  user(login: $login) {
    followers { totalCount }
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false,
                 orderBy: {field: PUSHED_AT, direction: DESC}) {
      totalCount
      nodes {
        name
        stargazerCount
        languages(first: 12, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name } }
        }
      }
    }
    contributionsCollection {
      totalCommitContributions
      totalPullRequestContributions
      contributionCalendar { totalContributions }
    }
  }
}
"""

W, H = 900, 224
PAD = 4
SEGMENTS = 5


def fetch():
    body = json.dumps({"query": QUERY, "variables": {"login": LOGIN}}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers={
            "Authorization": f"bearer {TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": "spec-card",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.load(resp)
    if "errors" in payload:
        raise SystemExit(f"GraphQL error: {payload['errors']}")
    return payload["data"]["user"]


def languages(repos):
    """Language mix across owned, non fork repositories.

    Each repository is normalised to its own 100 percent before being added up,
    so one repository carrying a large vendored tree cannot swamp the result.
    Raw byte totals answer "where do the bytes live"; this answers "what are the
    projects written in", which is the question the card is asking.
    """
    totals = {}
    counted = 0
    for repo in repos:
        edges = repo["languages"]["edges"]
        repo_bytes = sum(e["size"] for e in edges)
        if not repo_bytes:
            continue
        counted += 1
        for edge in edges:
            name = edge["node"]["name"]
            totals[name] = totals.get(name, 0) + edge["size"] / repo_bytes
    ranked = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)
    top = ranked[:SEGMENTS]
    rest = sum(size for _, size in ranked[SEGMENTS:])
    if rest:
        top.append(("Other", rest))
    grand = sum(size for _, size in top) or 1
    return [(name, size, size / grand * 100) for name, size in top], counted


def thousands(n):
    return f"{n:,}"


def spaced(s):
    """Letterspacing that survives any renderer, done in the string itself."""
    return " ".join(s)


# Monospace advance per character: font size times ratio, plus CSS tracking.
# The ratio runs slightly wide of the 0.6 most monospace faces use, so a
# viewer whose fallback font is a little broader still has room.
ADVANCE = {"meta": 9 * 0.62 + 1.6, "note": 9 * 0.62 + 0.5}


def label(x, y, text, cls="meta", right=False):
    """A small caps label. Right alignment is computed rather than left to
    text-anchor, which not every SVG renderer honours."""
    if right:
        x -= len(text) * ADVANCE[cls]
    return (
        f'<text class="{cls}" x="{x:.1f}" y="{y}" xml:space="preserve">{text}</text>'
    )


def build(user):
    repos = user["repositories"]["nodes"]
    contrib = user["contributionsCollection"]
    langs, scanned = languages(repos)
    stars = sum(r["stargazerCount"] for r in repos)

    stats = [
        (thousands(user["repositories"]["totalCount"]), "REPOSITORIES"),
        (thousands(contrib["contributionCalendar"]["totalContributions"]),
         "CONTRIBUTIONS"),
        (thousands(contrib["totalCommitContributions"]), "COMMITS"),
        (thousands(user["followers"]["totalCount"]), "FOLLOWERS"),
        (thousands(stars), "STARS EARNED"),
    ]

    parts = []
    css = []

    # One fade and rise step per column, shared by the stats and the legend.
    for i in range(max(len(stats), len(langs))):
        css.append(
            f"@keyframes rise{i}{{from{{opacity:0;transform:translateY(6px)}}"
            f"to{{opacity:1;transform:translateY(0)}}}}"
        )
        css.append(
            f".s{i}{{opacity:0;animation:rise{i} .5s ease-out "
            f"{0.15 + i * 0.07:.2f}s forwards}}"
        )

    stamp = datetime.now(timezone.utc).strftime("%d %b %Y").upper()
    parts.append(label(PAD, 16, spaced("PROFILE") + "   " + spaced("SPEC")))
    parts.append(label(W - PAD, 16, stamp, cls="note", right=True))
    parts.append(f'<line class="rule r0" x1="{PAD}" y1="28" x2="{W - PAD}" y2="28"/>')

    # Stat columns.
    step = (W - PAD * 2) / len(stats)
    for i, (value, caption) in enumerate(stats):
        x = PAD + step * i
        parts.append(
            f'<g class="stat s{i}">'
            f'<text class="num" x="{x:.1f}" y="76">{value}</text>'
            f'<text class="cap" x="{x:.1f}" y="94" xml:space="preserve">'
            f"{spaced(caption)}</text>"
            f"</g>"
        )

    parts.append(f'<line class="rule r1" x1="{PAD}" y1="118" x2="{W - PAD}" y2="118"/>')

    parts.append(label(PAD, 138, spaced("LANGUAGE") + "   " + spaced("MIX")))
    parts.append(
        label(W - PAD, 138, f"{scanned} REPOSITORIES, WEIGHTED EQUALLY",
              cls="note", right=True)
    )

    # Stacked language bar.
    bar_y, bar_h, bar_w = 150, 9, W - PAD * 2
    x = PAD
    for i, (name, _size, share) in enumerate(langs):
        seg = bar_w * share / 100
        parts.append(
            f'<rect class="seg g{i}" x="{x:.2f}" y="{bar_y}" '
            f'width="{seg:.2f}" height="{bar_h}"/>'
        )
        css.append(
            f"@keyframes grow{i}{{from{{width:0}}to{{width:{seg:.2f}px}}}}"
        )
        css.append(
            f".g{i}{{width:0;animation:grow{i} .8s cubic-bezier(.16,.84,.44,1) "
            f"{0.35 + i * 0.09:.2f}s forwards}}"
        )
        x += seg

    # Legend.
    lx = PAD
    for i, (name, _size, share) in enumerate(langs):
        parts.append(
            f'<g class="stat s{i}">'
            f'<rect class="seg g{i}k" x="{lx}" y="{bar_y + 30}" width="7" height="7"/>'
            f'<text class="leg" x="{lx + 13}" y="{bar_y + 37}">'
            f"{name} {share:.1f}%</text>"
            f"</g>"
        )
        lx += 16 + len(f"{name} {share:.1f}%") * 6.6

    # Legend swatches share the segment colours but not the grow animation.
    ramp_light = ["#24292f", "#4a515a", "#6e7781", "#8b949e", "#afb8c1", "#d0d7de"]
    ramp_dark = ["#e6edf3", "#c9d1d9", "#8b949e", "#6e7781", "#57606a", "#3d444d"]
    for i in range(len(langs)):
        css.append(f".g{i},.g{i}k{{fill:{ramp_light[i]}}}")
    dark_ramp = "".join(
        f".g{i},.g{i}k{{fill:{ramp_dark[i]}}}" for i in range(len(langs))
    )

    static = f"""
    text{{font-family:ui-monospace,SFMono-Regular,"SF Mono",Menlo,Consolas,
      "DejaVu Sans Mono",monospace}}
    .meta{{font-size:9px;letter-spacing:1.6px;fill:#8b949e}}
    .note{{font-size:9px;letter-spacing:.5px;fill:#afb8c1}}
    .num{{font-size:29px;fill:#24292f;letter-spacing:-.5px}}
    .cap{{font-size:8.5px;fill:#8b949e}}
    .leg{{font-size:10px;fill:#6e7781}}
    .rule{{stroke:#d0d7de;stroke-width:1}}
    .stat{{transform-box:fill-box}}
    @keyframes sweep{{from{{stroke-dashoffset:{W}}}to{{stroke-dashoffset:0}}}}
    .rule{{stroke-dasharray:{W};stroke-dashoffset:{W};
      animation:sweep 1s cubic-bezier(.16,.84,.44,1) forwards}}
    .r1{{animation-delay:.12s}}
    @media (prefers-color-scheme:dark){{
      .num{{fill:#e6edf3}}
      .meta,.cap{{fill:#6e7781}}
      .note{{fill:#484f58}}
      .leg{{fill:#8b949e}}
      .rule{{stroke:#30363d}}
      {dark_ramp}
    }}
    @media (prefers-reduced-motion:reduce){{
      *{{animation:none!important;opacity:1!important;stroke-dashoffset:0!important}}
    }}
    """

    described = ", ".join(f"{n} {s:.0f} percent" for n, _b, s in langs[:3])
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
        f'width="{W}" height="{H}" role="img" '
        f'aria-label="Profile statistics. Top languages: {described}.">'
        f"<style>{static}{''.join(css)}</style>" + "".join(parts) + "</svg>"
    )


if __name__ == "__main__":
    out = pathlib.Path("assets/spec-card.svg")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(build(fetch()), encoding="utf-8")
    print(f"wrote {out} ({out.stat().st_size} bytes)")
