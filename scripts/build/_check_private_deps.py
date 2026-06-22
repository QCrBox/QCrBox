#!/usr/bin/env python3
"""Check that all files listed in a private_build.yml are present in the app directory."""
import sys
import pathlib
import yaml

sentinel = pathlib.Path(sys.argv[1])
app_dir = pathlib.Path(sys.argv[2])

for req in yaml.safe_load(sentinel.read_text())["requires"]:
    if not (app_dir / req["filename"]).exists():
        print(f"ERROR: missing {app_dir / req['filename']}", file=sys.stderr)
        print(f"  {req['description']}", file=sys.stderr)
        sys.exit(1)
