#!/usr/bin/env python3
import argparse
from pathlib import Path
import xml.etree.ElementTree as ET
from library import render_layout

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Render a dynamic IOF dimension or route layout")
    parser.add_argument("reference", help="IOF reference, e.g. 9.3 or 15.1")
    parser.add_argument("--values", nargs="+", help="Dimension values in metres")
    parser.add_argument("--distance", help="Route distance in metres")
    parser.add_argument("--output", type=Path, help="Output SVG path; defaults to stdout")
    args = parser.parse_args()
    try:
        payload = ET.tostring(render_layout(args.reference, values=args.values, distance=args.distance), encoding="unicode") + "\n"
    except ValueError as error:
        parser.error(str(error))
    if args.output:
        args.output.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
