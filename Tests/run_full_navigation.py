#!/usr/bin/env python3
"""Run the adopted software navigation actor with a new synthetic profile root."""
from pathlib import Path
import subprocess
import sys
import tempfile
if len(sys.argv) != 3:
    raise SystemExit("usage: run_full_navigation.py EXECUTABLE RUNTIME_ASSETS")
parent = Path(tempfile.mkdtemp(prefix="fathom-full-navigation-")).resolve(strict=True)
raise SystemExit(subprocess.run([str(Path(sys.argv[1]).resolve(strict=True)), str(parent / "fixture"), str(Path(sys.argv[2]).resolve(strict=True))], check=False).returncode)
