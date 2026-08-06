"""Fold the generated calendar into the profile's grayscale.

The calendar itself already honours the palette in .github/calendar-settings.json,
but the composite also draws a language pie using GitHub's per language brand
colours, which are the only saturated thing on the page. Any colour the settings
file did not ask for is remapped onto the same ramp the spec card uses, in order
of first appearance, so the pie stays readable without breaking the page.
"""

import pathlib
import re

TARGET = pathlib.Path("profile-3d-contrib/calendar.svg")

# Colours the settings file asks for, plus the neutrals the renderer adds itself.
KEEP = {
    "#6e7781", "#8b949e", "#d0d7de", "#b1bac4", "#484f58",
    "#00000000", "#ffffff", "#000000",
}

RAMP = ["#24292f", "#4a515a", "#6e7781", "#8b949e", "#afb8c1", "#d0d7de"]


def main():
    svg = TARGET.read_text(encoding="utf-8")

    seen = []
    for colour in re.findall(r"#[0-9a-fA-F]{6,8}\b", svg):
        low = colour.lower()
        if low not in KEEP and low not in seen:
            seen.append(low)

    if not seen:
        print("Nothing to neutralise.")
        return

    for i, colour in enumerate(seen):
        grey = RAMP[i % len(RAMP)]
        svg = re.sub(re.escape(colour), grey, svg, flags=re.IGNORECASE)
        print(f"{colour} -> {grey}")

    TARGET.write_text(svg, encoding="utf-8")


if __name__ == "__main__":
    main()
