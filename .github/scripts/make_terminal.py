"""Render a real terminal session into a self contained animated SVG.

The transcript is genuine output from Rakesh173/DAA-Lab-Manual, experiment 10.
Nothing here loads at runtime: no fonts, no scripts, no external images.
"""

import html

FS = 12.5           # font size
CW = FS * 0.62      # monospace advance, sized generously so no line clips
LH = 19             # line height
X = 28              # left padding
TOP = 62            # baseline of the first content line
CYCLE = 16.0        # seconds for one full loop

CMD = "$ python3 Exp10_Randomized_QuickSort/quick_sort.py"

HEADER = "Input Type          DQS Comps   DQS Time(ms)    RQS Comps   RQS Time(ms)"
ROWS = [
    ("Random                  72787           5.54        68592           6.33", None),
    ("Sorted               12497500         961.91        66922           6.35", "961.91"),
    ("Reverse              12497500         729.44        71990           6.77", "729.44"),
    ("Nearly Sorted          240562          18.02        70523           6.46", None),
]

COLS = 72
WIDTH = X * 2 + COLS * CW
HEIGHT = 236


def pct(seconds):
    return round(seconds / CYCLE * 100, 3)


def keyframes(name, stops):
    body = " ".join(f"{k}%{{{v}}}" for k, v in stops)
    return f"@keyframes {name}{{{body}}}"


def text_line(y, content, highlight, cls):
    """One transcript line. Highlights stay inside the same text element so
    monospace columns keep their alignment."""
    if not highlight:
        inner = html.escape(content)
    else:
        i = content.index(highlight)
        inner = (
            html.escape(content[:i])
            + f'<tspan class="hi">{html.escape(highlight)}</tspan>'
            + html.escape(content[i + len(highlight):])
        )
    return (
        f'<text class="{cls}" x="{X}" y="{y}" xml:space="preserve">{inner}</text>'
    )


def build():
    css = []
    parts = []

    # Reveal schedule, in seconds along the cycle.
    t_type_start, t_type_end = 0.4, 2.2
    reveal = [2.5, 2.7, 2.95, 3.15, 3.35, 3.55]   # header, rule, four rows
    t_prompt = 4.0
    t_hold, t_gone = 13.4, 14.4

    # Frame and title bar.
    parts.append(
        f'<rect class="frame" x="0.5" y="0.5" width="{WIDTH - 1}" '
        f'height="{HEIGHT - 1}" rx="7"/>'
    )
    parts.append(
        f'<text class="chrome" x="{X}" y="26" xml:space="preserve">'
        f'D A A &#160; L A B &#160; M A N U A L</text>'
    )
    parts.append(
        f'<line class="chrome-rule" x1="0" y1="40" x2="{WIDTH}" y2="40"/>'
    )

    body = ['<g class="body">']

    # The command, typed out under a clip that widens.
    cmd_w = len(CMD) * CW + 12
    body.append(
        f'<clipPath id="type"><rect class="caret" x="{X}" y="{TOP - 14}" '
        f'width="{cmd_w}" height="{LH}"/></clipPath>'
    )
    body.append(f'<g clip-path="url(#type)">{text_line(TOP, CMD, None, "cmd")}</g>')
    css.append(
        keyframes("type", [(0, "width:0"), (pct(t_type_start), "width:0"),
                           (pct(t_type_end), f"width:{cmd_w}px"),
                           (100, f"width:{cmd_w}px")])
    )
    css.append(
        f".caret{{animation:type {CYCLE}s steps({len(CMD)},end) infinite}}"
    )

    y = TOP + LH * 2
    body.append(text_line(y, HEADER, None, "line l0"))

    y_rule = y + 8
    body.append(
        f'<line class="rule" x1="{X}" y1="{y_rule}" '
        f'x2="{X + COLS * CW}" y2="{y_rule}"/>'
    )
    span = COLS * CW
    css.append(
        keyframes("draw", [(0, f"stroke-dashoffset:{span}"),
                           (pct(reveal[1]), f"stroke-dashoffset:{span}"),
                           (pct(reveal[1] + 0.5), "stroke-dashoffset:0"),
                           (100, "stroke-dashoffset:0")])
    )
    css.append(
        f".rule{{stroke-dasharray:{span};animation:draw {CYCLE}s linear infinite}}"
    )

    y = y_rule + 12
    for n, (row, hi) in enumerate(ROWS):
        y += LH
        body.append(text_line(y, row, hi, f"line l{n + 1}"))

    # Prompt returns, cursor blinks.
    y_prompt = y + LH * 2
    body.append(text_line(y_prompt, "$", None, "cmd l5"))
    body.append(
        f'<rect class="cursor" x="{X + CW * 2}" y="{y_prompt - 10}" '
        f'width="{CW}" height="13"/>'
    )

    # Each revealed element gets its own step in the shared timeline.
    for n, t in enumerate(reveal):
        if n == 1:
            continue  # the rule draws itself instead of fading in
        idx = n if n == 0 else n - 1
        css.append(
            keyframes(f"show{idx}", [(0, "opacity:0"), (pct(t), "opacity:0"),
                                     (pct(t + 0.01), "opacity:1"),
                                     (100, "opacity:1")])
        )
        css.append(f".l{idx}{{animation:show{idx} {CYCLE}s steps(1,end) infinite}}")

    css.append(
        keyframes("show5", [(0, "opacity:0"), (pct(t_prompt), "opacity:0"),
                            (pct(t_prompt + 0.01), "opacity:1"), (100, "opacity:1")])
    )
    css.append(f".l5{{animation:show5 {CYCLE}s steps(1,end) infinite}}")

    css.append(
        keyframes("blink", [(0, "opacity:0"), (pct(t_prompt), "opacity:0"),
                            (pct(t_prompt + 0.01), "opacity:1"),
                            (pct(t_prompt + 0.5), "opacity:1"),
                            (pct(t_prompt + 0.51), "opacity:0"),
                            (pct(t_prompt + 1.0), "opacity:0"),
                            (pct(t_prompt + 1.01), "opacity:1"),
                            (pct(t_prompt + 1.5), "opacity:1"),
                            (pct(t_prompt + 1.51), "opacity:0"),
                            (100, "opacity:0")])
    )
    css.append(f".cursor{{animation:blink {CYCLE}s steps(1,end) infinite}}")

    # Fade the whole transcript out so the loop does not snap.
    css.append(
        keyframes("cycle", [(0, "opacity:1"), (pct(t_hold), "opacity:1"),
                            (pct(t_gone), "opacity:0"), (100, "opacity:0")])
    )
    css.append(f".body{{animation:cycle {CYCLE}s linear infinite}}")

    body.append("</g>")
    parts.extend(body)

    static = f"""
    text{{font-family:ui-monospace,SFMono-Regular,"SF Mono",Menlo,Consolas,
      "DejaVu Sans Mono",monospace;font-size:{FS}px}}
    .frame{{fill:none;stroke:#d0d7de}}
    .chrome{{font-size:9px;letter-spacing:1.5px;fill:#8b949e}}
    .chrome-rule{{stroke:#d0d7de;stroke-width:1}}
    .cmd{{fill:#8b949e}}
    .line{{fill:#6e7781}}
    .hi{{fill:#24292f;font-weight:600}}
    .rule{{stroke:#d0d7de;stroke-width:1}}
    .cursor{{fill:#8b949e}}
    @media (prefers-color-scheme:dark){{
      .frame,.chrome-rule,.rule{{stroke:#30363d}}
      .cmd,.chrome,.cursor{{fill:#6e7781}}
      .line{{fill:#8b949e}}
      .hi{{fill:#e6edf3}}
    }}
    @media (prefers-reduced-motion:reduce){{
      *{{animation:none!important}}
      .caret{{width:{cmd_w}px}}
      .line,.cmd,.rule,.cursor{{opacity:1;stroke-dashoffset:0}}
    }}
    """

    style = static + "".join(css)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH:.0f} {HEIGHT}" '
        f'width="{WIDTH:.0f}" height="{HEIGHT}" role="img" '
        f'aria-label="Terminal session comparing deterministic and randomized quick sort">'
        f'<title>Deterministic quick sort degrades to 961 ms on sorted input. '
        f'Randomized quick sort holds at 6 ms.</title>'
        f"<style>{style}</style>" + "".join(parts) + "</svg>"
    )


if __name__ == "__main__":
    import pathlib
    out = pathlib.Path(__file__).with_name("terminal.svg")
    out.write_text(build(), encoding="utf-8")
    print(f"wrote {out} ({out.stat().st_size} bytes)")
