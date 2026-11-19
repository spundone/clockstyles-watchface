#!/usr/bin/env python3
"""Writes a throwaway watchface.xml that probes renderer features (run gen.py afterwards to restore)."""
from pathlib import Path
rows = []
def pt(y, expr, label, extra="", x=0, w=450, size=40, color="#FFFFFFFF", family="gsf_heavy", tmpl="%s"):
    params = "".join(f'<Parameter expression="{e}" />' for e in expr)
    rows.append(f'''<PartText x="{x}" y="{y}" width="{w}" height="{int(size*1.3)}"><Text align="CENTER">
<Font family="{family}" size="{size}" color="{color}">{extra}<Template>{tmpl}<Parameter expression="0" /></Template></Font></Text></PartText>''' if False else
f'''<PartText x="{x}" y="{y}" width="{w}" height="{int(size*1.3)}"><Text align="CENTER">
<Font family="{family}" size="{size}" color="{color}">{extra}<Template>{tmpl}{params}</Template></Font></Text></PartText>''')
pt(40, ["floor([HOUR_1_12] / 10)", "[HOUR_1_12] % 10"], "", tmpl="A%s B%s", family="gsf_text", size=34)
pt(85, ["subText([HOUR_1_12_Z], 0, 1)", "subText([HOUR_1_12_Z], 1, 2)"], "", tmpl="C%s D%s", family="gsf_text", size=34)
pt(130, ["floor([MINUTE] / 10)", "[MINUTE] % 10"], "", tmpl="E%s F%s", family="gsf_text", size=34)
# outline test: two overlapping digits
rows.append('''<PartText x="105" y="180" width="160" height="150"><Text align="CENTER"><Font family="gsf_heavy" size="140" color="#FFE6F7FB"><Template>0</Template></Font></Text></PartText>''')
rows.append('''<PartText x="185" y="180" width="160" height="150"><Text align="CENTER"><Font family="gsf_heavy" size="140" color="#FF9DD9EA"><Outline color="#FF000000" width="10" /><Template>2</Template></Font></Text></PartText>''')
# rotated label
rows.append('''<PartText x="20" y="330" width="200" height="40" angle="-30"><Text align="CENTER"><Font family="gsf_text" size="28" color="#FFFFD080"><Template>ROT</Template></Font></Text></PartText>''')
# circular text
rows.append('''<PartText x="0" y="0" width="450" height="450"><TextCircular centerX="225" centerY="225" width="400" height="400" startAngle="200" endAngle="340" direction="CLOCKWISE" isOutside="TRUE"><Font family="gsf_text" size="28" color="#FF80FF80"><Template>CIRCLE %s<Parameter expression="[DAY]" /></Template></Font></TextCircular></PartText>''')
xml = f'''<?xml version="1.0" encoding="utf-8"?>
<WatchFace width="450" height="450"><Metadata key="CLOCK_TYPE" value="DIGITAL" /><Metadata key="PREVIEW_TIME" value="10:08:32" />
<Scene backgroundColor="#FF000000">
{chr(10).join(rows)}
</Scene></WatchFace>'''
(Path(__file__).resolve().parent.parent / "res/raw/watchface.xml").write_text(xml)
