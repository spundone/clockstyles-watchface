#!/usr/bin/env python3
"""Cuts small static digit fonts from Google Sans Flex (OFL) into res/font/.

Usage: cut_fonts.py path/to/GoogleSansFlex[ROND,opsz,slnt,wdth,wght].ttf
Needs fontTools. Each cut keeps only digits, colon and space, so it stays ~10-15 KB.
"""
import sys
from pathlib import Path

from fontTools.ttLib import TTFont
from fontTools.varLib import instancer
from fontTools import subset

# name: axis pins
CUTS = {
    "gsf_narrow":       dict(wght=560, ROND=0,   wdth=25,  opsz=144),  # Narrow
    "gsf_thin":         dict(wght=110, ROND=0,   wdth=100, opsz=144),  # Thin
    "gsf_medium_round": dict(wght=600, ROND=100, wdth=112, opsz=144),  # Pill
    "gsf_heavy":        dict(wght=1000, ROND=100, wdth=125, opsz=144), # Sticker, Line
}
TEXT = "0123456789: "


def main(src):
    out = Path(__file__).resolve().parent.parent / "res/font"
    for name, pins in CUTS.items():
        f = TTFont(src)
        f = instancer.instantiateVariableFont(f, {**pins, "slnt": 0})
        opts = subset.Options()
        opts.layout_features = ["tnum", "lnum"]  # tabular digits so the time doesn't jiggle
        opts.name_IDs = ["*"]
        opts.notdef_outline = True
        s = subset.Subsetter(opts)
        s.populate(text=TEXT)
        s.subset(f)
        path = out / f"{name}.ttf"
        f.save(path)
        print(f"{path.name}: {path.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main(sys.argv[1])
