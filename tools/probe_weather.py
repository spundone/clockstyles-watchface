#!/usr/bin/env python3
"""Throwaway face probing WFF v2 weather and battery sources (run gen.py afterwards to restore)."""
from pathlib import Path
exprs = ["[WEATHER.IS_AVAILABLE]", "[WEATHER.TEMPERATURE]", "[WEATHER.CONDITION]", "[WEATHER.TEMPERATURE_UNIT]",
         "[WEATHER.DAY_TEMPERATURE_HIGH]", "[WEATHER.DAY_TEMPERATURE_LOW]", "[BATTERY_CHARGING_STATUS]", "[BATTERY_IS_LOW]"]
rows = "\n".join(
    f'<PartText x="20" y="{60 + i * 40}" width="410" height="38"><Text align="CENTER"><Font family="gsf_text" size="26" color="#FFFFFFFF">'
    f'<Template>{e[1:-1]}=%s<Parameter expression="{e}" /></Template></Font></Text></PartText>' for i, e in enumerate(exprs))
xml = f'''<?xml version="1.0" encoding="utf-8"?>
<WatchFace width="450" height="450"><Metadata key="CLOCK_TYPE" value="DIGITAL" /><Metadata key="PREVIEW_TIME" value="10:08:32" />
<Scene backgroundColor="#FF000000">
{rows}
</Scene></WatchFace>'''
(Path(__file__).resolve().parent.parent / "res/raw/watchface.xml").write_text(xml)
