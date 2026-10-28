#!/usr/bin/env python3
"""Run an explicit-root storage fixture without opening a user's profile.

Each invocation gets a new synthetic directory. Keep it for diagnosis rather
than reusing or overwriting a previous test's records.
"""
from pathlib import Path
import subprocess
import sys
import tempfile

if len(sys.argv) != 2:
    raise SystemExit("usage: run_with_fresh_root.py TEST_EXECUTABLE")
executable = Path(sys.argv[1]).resolve(strict=True)
parent = Path(tempfile.mkdtemp(prefix="fathom-storage-test-")).resolve(strict=True)
raise SystemExit(subprocess.run([str(executable), str(parent / "fixture")], check=False).returncode)
