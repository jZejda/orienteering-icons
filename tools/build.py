#!/usr/bin/env python3
import argparse
import json
from library import build, validate

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate and build the SVG library")
    parser.add_argument("--check", action="store_true", help="Validate sources without writing build output")
    args = parser.parse_args()
    print(json.dumps(validate() if args.check else build(), indent=2))
