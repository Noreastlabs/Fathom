#!/usr/bin/env python3
"""Check byte-preserving, no-op CMake generation without configuring the App."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile
import os


INPUTS = {
    "Source/storage/ProfileSchema.sql": "FATHOM_PROFILE_SCHEMA",
    "Source/progression/InitialRules.json": "FATHOM_PROGRESSION_RULES",
    "Source/progression/SourceRubrics.json": "FATHOM_PROGRESSION_SOURCE",
}
TEMPLATES = {
    "Source/storage/ProfileSchema.generated.hpp.in": "ProfileSchema.generated.hpp",
    "Source/progression/ProgressionRules.generated.hpp.in": "ProgressionRules.generated.hpp",
}


def expected(inputs):
    # Independent goldens preserve the previous file(WRITE) byte format.
    return {
        "ProfileSchema.generated.hpp": b'#pragma once\ninline constexpr const char* profileSchemaSql=R"FathomSchema('
        + inputs["Source/storage/ProfileSchema.sql"] + b')FathomSchema";\n',
        "ProgressionRules.generated.hpp": b'#pragma once\ninline constexpr const char* progressionInitialRules=R"FathomRules('
        + inputs["Source/progression/InitialRules.json"] + b')FathomRules";\n'
        + b'inline constexpr const char* progressionSourceRules=R"FathomSource('
        + inputs["Source/progression/SourceRubrics.json"] + b')FathomSource";\n',
    }


def run_checks(root, scratch_parent):
    source = (root / "CMakeLists.txt").read_text()
    calls = []
    checks = []

    def check(value, name):
        if not value:
            raise AssertionError(name)
        checks.append(name)

    for path, variable in INPUTS.items():
        read_call = f'file(READ "${{CMAKE_CURRENT_SOURCE_DIR}}/{path}" {variable})'
        check(source.count(read_call) == 1, f"One exact source READ: {path}")
        calls.append(read_call)
        depends = re.findall(r'set_property\(DIRECTORY APPEND PROPERTY CMAKE_CONFIGURE_DEPENDS\s+([^)]*)\)', source)
        check(sum(f'"${{CMAKE_CURRENT_SOURCE_DIR}}/{path}"' in block for block in depends) == 1,
              f"Source configure dependency retained: {path}")
    for template, output in TEMPLATES.items():
        pattern = (r'configure_file\(\s*"\$\{CMAKE_CURRENT_SOURCE_DIR\}/'
                   + re.escape(template) + r'"\s*"\$\{CMAKE_CURRENT_BINARY_DIR\}/'
                   + re.escape(output) + r'"\s*@ONLY\s*\)')
        found = re.findall(pattern, source)
        check(len(found) == 1, f"One actual @ONLY configure call: {output}")
        calls.append(found[0])
        check(not re.search(r'file\(WRITE\s+"\$\{CMAKE_CURRENT_BINARY_DIR\}/'
                            + re.escape(output) + r'"', source),
              f"No unconditional write remains: {output}")

    inputs = {path: (root / path).read_bytes() for path in INPUTS}
    templates = {path: (root / path).read_bytes() for path in TEMPLATES}
    refs = [{"path": path, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
            for path, data in {"CMakeLists.txt": source.encode(), **inputs, **templates}.items()]
    sentinel = 946684800000000000
    with tempfile.TemporaryDirectory(prefix="fathom-header-configure-", dir=scratch_parent) as name:
        fixture = Path(name)
        output = fixture / "generated"
        output.mkdir()
        for path, data in {**inputs, **templates}.items():
            target = fixture / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        recipe = fixture / "check.cmake"
        recipe.write_text(f'set(CMAKE_CURRENT_SOURCE_DIR "{fixture.as_posix()}")\n'
                          + f'set(CMAKE_CURRENT_BINARY_DIR "{output.as_posix()}")\n'
                          + "\n".join(calls) + "\n")

        def configure():
            result = subprocess.run(["cmake", "-P", str(recipe)], capture_output=True,
                                    text=True, timeout=20)
            check(result.returncode == 0, "Isolated actual configure calls exit0")
            if result.returncode:
                raise AssertionError(result.stdout + result.stderr)

        def verify_bytes(values, label):
            for path, golden in expected(values).items():
                check((output / path).read_bytes() == golden, f"Exact previous byte format: {label}/{path}")

        configure()
        verify_bytes(inputs, "accepted-inputs")
        for path in TEMPLATES.values():
            os.utime(output / path, ns=(sentinel, sentinel))
        configure()
        verify_bytes(inputs, "no-op")
        for path in TEMPLATES.values():
            check((output / path).stat().st_mtime_ns == sentinel, f"No-op preserves output mtime: {path}")

        # These copied text fixtures test escaping/expansion, not runtime schema approval.
        special = '\nfixture ${literal} @literal@; "quotes"; café —\n'.encode()
        for changed in INPUTS:
            for path, data in inputs.items():
                (fixture / path).write_bytes(data)
            configure()
            for path in TEMPLATES.values():
                os.utime(output / path, ns=(sentinel, sentinel))
            values = dict(inputs)
            values[changed] += special
            (fixture / changed).write_bytes(values[changed])
            configure()
            verify_bytes(values, changed)
            affected = ("ProfileSchema.generated.hpp" if "ProfileSchema.sql" in changed
                        else "ProgressionRules.generated.hpp")
            for path in TEMPLATES.values():
                check(((output / path).stat().st_mtime_ns != sentinel) == (path == affected),
                      f"Only changed input's output is rewritten: {changed}/{path}")

    return {"status": "PASS", "checks": len(checks), "check_names": checks,
            "input_refs": refs, "accepted_generated_goldens": [
                {"path": path, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
                for path, data in expected(inputs).items()],
            "isolated_cmake_invocations": 8, "product_configure_build_launches": 0,
            "temporary_outputs": "Removed after byte/mtime comparisons by owned TemporaryDirectory",
            "source_input_changes": 0, "acceptance_increment": 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--scratch-parent", type=Path)
    args = parser.parse_args()
    root = args.root.resolve(strict=True)
    actual = subprocess.check_output(["git", "-C", str(root), "rev-parse", "--show-toplevel"], text=True).strip()
    if actual != str(root):
        raise SystemExit("Expected authoritative Git root")
    print(json.dumps(run_checks(root, args.scratch_parent), ensure_ascii=False))


if __name__ == "__main__":
    main()
