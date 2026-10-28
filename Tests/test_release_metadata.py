"""Synthetic parser/custody tests: no real-App read, shell, tool or product run."""
from dataclasses import replace
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import plistlib
import shlex
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

MODULE_PATH = Path(__file__).resolve().parents[1] / "Tools" / "fathom_release_metadata.py"
SPEC = importlib.util.spec_from_file_location("release_build_metadata_candidate", MODULE_PATH)
M = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = M
SPEC.loader.exec_module(M)


class SyntheticFixture:
    def __init__(self, root):
        self.root = root
        self.build = root / "Build/recipe with spaces"
        self.app = self.build / "Fathom artefacts/Debug/Fathom.app"
        self.exe = self.app / "Contents/MacOS/Fathom"
        self.plist = self.app / "Contents/Info.plist"
        self.cache = self.build / "CMakeCache.txt"
        self.link = self.build / "CMakeFiles/Fathom.dir/link.txt"
        self.out = root / "Results/fresh metadata"
        for p, data in {
            self.exe: b"Synthetic bytes; this is not a runnable App executable.",
            self.plist: plistlib.dumps({"CFBundleExecutable": "Fathom", "CFBundleVersion": "0.1.0"}),
            self.app / "Contents/PkgInfo": b"APPL????",
            self.cache: (f"CMAKE_HOME_DIRECTORY:INTERNAL={root}\n"
                         f"Fathom_SOURCE_DIR:STATIC={root}\n"
                         f"Fathom_BINARY_DIR:STATIC={self.build}\n"
                         "CMAKE_BUILD_TYPE:STRING=Debug\n").encode(),
            self.build / "CMakeFiles/Fathom.dir/flags.make":
                b"CXX_DEFINES = -DJUCE_WEB_BROWSER=0 -DJUCE_USE_CURL=0\n",
            self.link: (shlex.join(["/usr/bin/c++", "fake.o", "-o",
                                   str(self.exe.relative_to(self.build)),
                                   "libfathom_core.a", "libfathom_sqlite.a"]) + "\n").encode(),
            root / "CMakeLists.txt": b"project(Fathom VERSION 0.1.0)\n",
            root / "CMakePresets.json": b"{}\n",
            root / "Dependencies/lock.json": b"{}\n",
            root / "Dependencies/NOTICE.md": b"Synthetic terms reference; no real dependency copied.\n",
        }.items():
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(data)
        self.out.parent.mkdir(exist_ok=True)
        self.sha = hashlib.sha256(self.exe.read_bytes()).hexdigest()
        self.request = M.Request(root, self.build, self.app, self.sha, self.out)
        self.calls = []
        self.override = None
        self.dependencies = ["/System/Library/Frameworks/AppKit.framework/Versions/C/AppKit",
                             "/usr/lib/libc++.1.dylib"]

    def runner(self, argv, root, timeout):
        self.calls.append((argv, root, timeout))
        if self.override:
            result = self.override(argv)
            if result is not None:
                return result
        tool = argv[0]
        stdout, stderr = "", ""
        if tool.endswith("/git"):
            stdout = str(self.root) + "\n"
        elif tool.endswith("/sw_vers"):
            stdout = "ProductName: macOS\nProductVersion: 26.5.2\nBuildVersion: 25F84\n"
        elif tool.endswith("/uname"):
            stdout = "arm64\n"
        elif tool.endswith("/file"):
            stdout = str(self.exe) + ": Mach-O 64-bit executable arm64\n"
        elif tool.endswith("/lipo"):
            stdout = "arm64\n"
        elif tool.endswith("/otool") and argv[1] == "-L":
            stdout = str(self.exe) + ":\n" + "".join(
                "\t" + p + " (compatibility version 1.0.0, current version 1.0.0)\n"
                for p in self.dependencies)
        elif tool.endswith("/otool") and argv[1] == "-l":
            stdout = (str(self.exe) + ":\nLoad command 10\n"
                      "      cmd LC_BUILD_VERSION\n cmdsize 32\n platform 1\n"
                      "    minos 11.0\n      sdk 26.5\n   ntools 1\n"
                      "     tool 3\n  version 1267.0\n")
        elif tool.endswith("/codesign"):
            stderr = "Signature=adhoc\nInfo.plist=not bound\nTeamIdentifier=not set\nSealed Resources=none\n"
        else:
            raise AssertionError("Unexpected command: " + repr(argv))
        return M.CommandResult(argv, 0, stdout, stderr)

    def tree(self):
        # Synthetic test inputs only, never the real App/corpus.
        return {p.relative_to(self.root).as_posix(): p.read_bytes()
                for p in self.root.rglob("*") if p.is_file() and not p.is_symlink()}


class MetadataCandidateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="fathom-metadata-synthetic-")
        self.addCleanup(self.temp.cleanup)
        self.f = SyntheticFixture(Path(self.temp.name).resolve())

    def fail_without_output(self, request=None, pattern=None):
        with self.assertRaises(M.AuditError) as caught:
            M.collect(request or self.f.request, runner=self.f.runner)
        if pattern:
            self.assertIn(pattern, str(caught.exception))
        self.assertFalse(self.f.out.exists())

    def test_success_preserves_input_tree_and_uses_bounded_literal_argv(self):
        before = self.f.tree()
        request, data, readback = M.collect(self.f.request, runner=self.f.runner)
        self.assertEqual(before, self.f.tree())
        self.assertFalse(self.f.out.exists())
        self.assertEqual(len(readback), 8)
        self.assertEqual(len(data["fresh_guarded_input_refs"]), 10)
        self.assertEqual(data["selected_executable"]["sha256"], self.f.sha)
        self.assertTrue(data["all_dynamic_load_paths_in_system_directories"])
        self.assertEqual(data["link_recipe"]["unique_project_static_archives_in_recipe"],
                         ["libfathom_core.a", "libfathom_sqlite.a"])
        self.assertFalse(data["strict_signature_verification_run"])
        self.assertFalse(data["Gatekeeper_assessment_run"])
        self.assertEqual(data["product_builds_launches_tests_GUI_profile_actions"], 0)
        for argv, root, timeout in self.f.calls:
            self.assertIsInstance(argv, tuple)
            self.assertEqual(root, self.f.root)
            self.assertEqual(timeout, 15.0)
            self.assertNotIn("--verify", argv)
            self.assertNotEqual(argv[0], str(self.f.exe))
        M.publish(request, data, readback)
        self.assertEqual({p.name for p in self.f.out.iterdir()},
                         {"current-build-metadata.json", "metadata-command-readback.json"})
        self.assertEqual(json.loads((self.f.out / "current-build-metadata.json").read_text()), data)
        after = self.f.tree()
        self.assertEqual({k: after[k] for k in before}, before)

    def test_dependency_paths_with_spaces_are_preserved_and_classified(self):
        self.f.dependencies = ["/usr/lib/Library With Spaces.dylib",
                               "/opt/Private Runtime/lib with spaces.dylib"]
        _, data, _ = M.collect(self.f.request, runner=self.f.runner)
        self.assertEqual(data["dynamic_load_paths"], self.f.dependencies)
        self.assertFalse(data["all_dynamic_load_paths_in_system_directories"])

    def test_retained_Metal_and_MetalKit_weak_rows_preserve_typed_qualifier(self):
        # Exact two row texts from the retained87e8 readback, with synthetic header.
        rows = ("\t/System/Library/Frameworks/Metal.framework/Versions/A/Metal (compatibility version 1.0.0, current version 373.2.0, weak)\n"
                "\t/System/Library/Frameworks/MetalKit.framework/Versions/A/MetalKit (compatibility version 1.0.0, current version 173.7.0, weak)\n")
        parsed = M.parse_otool_dependency_records(str(self.f.exe) + ":\n" + rows, self.f.exe)
        self.assertEqual(len(parsed), 2)
        self.assertEqual([r["weak"] for r in parsed], [True, True])
        self.assertEqual([r["current_version"] for r in parsed], ["373.2.0", "173.7.0"])
        self.assertEqual([r["compatibility_version"] for r in parsed], ["1.0.0", "1.0.0"])

    def test_weak_rows_reject_unknown_or_malformed_tails(self):
        for tail in [", upward", ", weak, reexport", ", weak weak", ", weak,", ",weak", ", weak junk"]:
            with self.subTest(tail=tail), self.assertRaises(M.AuditError):
                M.parse_otool_dependency_records(
                    str(self.f.exe) + ":\n\t/usr/lib/a (compatibility version 1.0.0, current version 1.0.0" + tail + ")\n",
                    self.f.exe)

    def test_collection_preserves_weak_and_strong_records(self):
        original = self.f.runner
        def weak_runner(argv, root, timeout):
            result = original(argv, root, timeout)
            if argv[0].endswith("/otool") and argv[1] == "-L":
                lines = result.stdout.splitlines()
                lines[1] = lines[1][:-1] + ", weak)"
                return M.CommandResult(argv, 0, "\n".join(lines) + "\n", "")
            return result
        _, data, _ = M.collect(self.f.request, runner=weak_runner)
        self.assertEqual([r["weak"] for r in data["dynamic_load_records"]], [True, False])
        self.assertEqual(data["dynamic_load_paths"], [r["path"] for r in data["dynamic_load_records"]])

    def test_dependency_parser_refuses_empty_or_dropped_rows(self):
        header = str(self.f.exe) + ":\n"
        for body in ["", "\n", "\t/usr/lib/a.dylib (unexpected fields)\n",
                     "\t/usr/lib/a.dylib (compatibility version 1..0, current version 1.0)\n",
                     "\t/usr/lib/a.dylib (compatibility version 1.0, current version 1.0)\nUNPARSED\n"]:
            with self.subTest(body=body), self.assertRaises(M.AuditError):
                M.parse_otool_dependencies(header + body, self.f.exe)

    def test_dependency_parser_refuses_wrong_header_or_control_path(self):
        for text in ["wrong:\n\t/usr/lib/a (compatibility version 1.0, current version 1.0)\n",
                     str(self.f.exe) + ":\n\t/usr/lib/evil\tname (compatibility version 1.0, current version 1.0)\n"]:
            with self.subTest(text=text), self.assertRaises(M.AuditError):
                M.parse_otool_dependencies(text, self.f.exe)

    def test_macho_build_minimum_does_not_parse_tool_version_as_OS(self):
        _, data, _ = M.collect(self.f.request, runner=self.f.runner)
        self.assertEqual(data["MachO_build_version"]["configured_load_command_minimum"], "11.0")
        self.assertFalse(data["MachO_build_version"]["minimum_supported_OS_observed"])

    def test_macho_legacy_version_and_ambiguous_or_missing_commands(self):
        text = str(self.f.exe) + ":\nLoad command 1\n cmd LC_VERSION_MIN_MACOSX\n version 11.0\n sdk 26.5\n"
        self.assertEqual(M.parse_load_version(text, self.f.exe)["build_sdk"], "26.5")
        for wrong in [str(self.f.exe) + ":\n", text + text.split(":\n", 1)[1],
                      text.replace(" sdk 26.5\n", ""), text.replace("version 11.0", "version garbage")]:
            with self.subTest(wrong=wrong), self.assertRaises(M.AuditError):
                M.parse_load_version(wrong, self.f.exe)

    def test_request_rejects_bad_digest_and_root_path_escape(self):
        for sha in ["", "a" * 63, "A" * 64, "g" * 64]:
            with self.subTest(sha=sha):
                self.fail_without_output(replace(self.f.request, expected_executable_sha256=sha))
        self.fail_without_output(replace(self.f.request, build=Path("../elsewhere")), "traversal")
        self.fail_without_output(replace(self.f.request, app=self.f.root.parent), "escapes")
        self.assertEqual(self.f.calls, [])

    def test_request_rejects_app_outside_build_and_output_in_build(self):
        self.fail_without_output(replace(self.f.request, app=self.f.root / "Dependencies"), "inside")
        self.fail_without_output(replace(self.f.request, out=self.f.build / "output"), "outside")
        self.fail_without_output(replace(self.f.request, out=self.f.root / "Dependencies/output"), "controls")

    def test_protected_namespace_aliases_refused_before_commands_or_output(self):
        for alias in ["Docs", "DOCS", "source", "sOuRcE", "tools", "TESTS", "content", "DEPENDENCIES", ".GiT"]:
            with self.subTest(alias=alias):
                parent = self.f.root / alias
                parent.mkdir(exist_ok=True)
                target = parent / "fresh"
                with self.assertRaisesRegex(M.AuditError, "controls"):
                    M.collect(replace(self.f.request, out=target), runner=self.f.runner)
                self.assertFalse(target.exists())
        self.assertEqual(self.f.calls, [])

    def test_build_and_App_component_aliases_refused_and_prefix_siblings_allowed(self):
        # Create alias spellings explicitly so this test works on either kind of filesystem.
        for alias in ["build/recipe with spaces", "BUILD/RECIPE WITH SPACES",
                      "build/recipe with spaces/FATHOM ARTEFACTS/debug/fathom.APP"]:
            with self.subTest(alias=alias):
                parent = self.f.root / alias
                parent.mkdir(parents=True, exist_ok=True)
                target = parent / "fresh"
                with self.assertRaisesRegex(M.AuditError, "outside"):
                    M.collect(replace(self.f.request, out=target), runner=self.f.runner)
                self.assertFalse(target.exists())
        self.assertEqual(self.f.calls, [])
        sibling = self.f.root / "Build/recipe with spaces-extra"
        sibling.mkdir()
        req = M.normalize_request(replace(self.f.request, out=sibling / "fresh"))
        self.assertEqual(req.out, sibling / "fresh")
        self.assertTrue(M.casefold_descendant(Path("/Root/BUILD/App.app/out"), Path("/root/build/app.APP")))
        self.assertFalse(M.casefold_descendant(Path("/Root/Build-extra/out"), Path("/root/build")))

    def test_existing_output_is_preserved_without_commands(self):
        self.f.out.mkdir()
        marker = self.f.out / "do-not-touch"
        marker.write_bytes(b"retained")
        with self.assertRaisesRegex(M.AuditError, "fresh"):
            M.collect(self.f.request, runner=self.f.runner)
        self.assertEqual(marker.read_bytes(), b"retained")
        self.assertEqual(self.f.calls, [])

    def test_output_parent_must_exist(self):
        self.fail_without_output(replace(self.f.request, out=self.f.root / "missing/leaf"), "Missing")
        self.assertFalse((self.f.root / "missing").exists())

    def test_symlink_root_app_input_and_output_parent_are_refused(self):
        link = self.f.root / "alias"
        link.symlink_to(self.f.build, target_is_directory=True)
        self.fail_without_output(replace(self.f.request, build=link), "Symlink")
        self.fail_without_output(replace(self.f.request, out=link / "fresh"), "Symlink")
        root_link = self.f.root / "root-alias"
        root_link.symlink_to(self.f.root, target_is_directory=True)
        self.fail_without_output(replace(self.f.request, root=root_link), "Symlink")
        app_link = self.f.build / "App-alias.app"
        app_link.symlink_to(self.f.app, target_is_directory=True)
        self.fail_without_output(replace(self.f.request, app=app_link), "Symlink")
        self.f.exe.unlink()
        self.f.exe.symlink_to(self.f.plist)
        self.fail_without_output(pattern="Symlink")

    def test_missing_metadata_is_refused_before_commands_or_output(self):
        self.f.link.unlink()
        before = self.f.tree()
        self.fail_without_output(pattern="Missing")
        self.assertEqual(before, self.f.tree())
        self.assertEqual(self.f.calls, [])

    def test_wrong_expected_executable_is_refused_before_commands(self):
        self.fail_without_output(replace(self.f.request, expected_executable_sha256="0" * 64), "SHA-256 drift")
        self.assertEqual(self.f.calls, [])

    def test_cache_missing_duplicate_and_contradictory_roots(self):
        original = self.f.cache.read_bytes()
        alternatives = [original.replace(b"CMAKE_HOME_DIRECTORY", b"NOT_THE_HOME"),
                        original + f"Fathom_SOURCE_DIR:STATIC={self.f.root}\n".encode(),
                        original.replace(str(self.f.build).encode(), str(self.f.root).encode()),
                        original.replace(b"CMAKE_BUILD_TYPE:STRING=Debug", b"CMAKE_BUILD_TYPE:STRING=")]
        for data in alternatives:
            with self.subTest(data=data):
                self.f.cache.write_bytes(data)
                self.fail_without_output(pattern="CMakeCache")
        self.assertEqual(self.f.calls, [])

    def test_link_output_missing_ambiguous_escape_and_wrong_App(self):
        for argv in [["/usr/bin/c++", "libfathom_core.a"],
                     ["/usr/bin/c++", "-o", str(self.f.exe), "-o", str(self.f.exe), "libfathom_core.a"],
                     ["/usr/bin/c++", "-o", "../../escape", "libfathom_core.a"],
                     ["/usr/bin/c++", "-o", str(self.f.plist), "libfathom_core.a"],
                     ["/usr/bin/c++", "-o", str(self.f.exe), "libfathom_core.a", "&&", "evil"]]:
            with self.subTest(argv=argv), self.assertRaises(M.AuditError):
                M.parse_link(shlex.join(argv).encode(), self.f.root, self.f.build, self.f.exe)

    def test_Git_root_mismatch_stops_before_other_commands(self):
        self.f.override = lambda argv: M.CommandResult(argv, 0, "/wrong/root\n", "") if argv[0].endswith("/git") else None
        self.fail_without_output(pattern="Git")
        self.assertEqual(len(self.f.calls), 1)

    def test_failed_timed_out_and_mismatched_commands_do_not_publish(self):
        for outcome in ["exit", "timeout", "argv"]:
            with self.subTest(outcome=outcome):
                def fail(argv):
                    if argv[0].endswith("/otool"):
                        if outcome == "timeout":
                            raise subprocess.TimeoutExpired(argv, 15)
                        return M.CommandResult(argv if outcome == "exit" else ("different",),
                                               3 if outcome == "exit" else 0, "", "failure")
                self.f.override = fail
                before = self.f.tree()
                self.fail_without_output()
                self.assertEqual(before, self.f.tree())

    def test_actual_runner_uses_timeout_no_shell_and_bounded_capture(self):
        seen = []
        def fake_run(argv, **kwargs):
            seen.append((argv, kwargs))
            kwargs["stdout"].write(b"bounded fake result")
            return subprocess.CompletedProcess(argv, 0)
        with patch.object(M.subprocess, "run", fake_run):
            result = M.command_runner(("/usr/bin/otool", "-L", str(self.f.exe)), self.f.root, 15)
        self.assertEqual(result.stdout, "bounded fake result")
        self.assertEqual(seen[0][1]["timeout"], 15)
        self.assertNotIn("shell", seen[0][1])
        with patch.object(M.subprocess, "run", side_effect=subprocess.TimeoutExpired("fake", 15)):
            with self.assertRaisesRegex(M.AuditError, "timed out"):
                M.command_runner(("fake",), self.f.root, 15)

    def test_actual_runner_size_check_occurs_after_mock_command_exit(self):
        exit_returned = []
        def write_large(argv, **kwargs):
            kwargs["stdout"].write(b"x" * (M.MAX_COMMAND_BYTES + 1))
            exit_returned.append(True)
            return subprocess.CompletedProcess(argv, 0)
        with patch.object(M.subprocess, "run", write_large), self.assertRaisesRegex(M.AuditError, "output size"):
            M.command_runner(("fake-read-only-tool",), self.f.root, 15)
        self.assertEqual(exit_returned, [True])
        self.assertFalse(self.f.out.exists())

    def test_command_output_bound_and_unparsed_architecture(self):
        self.f.override = lambda argv: M.CommandResult(argv, 0, "x" * (M.MAX_COMMAND_BYTES + 1), "")
        self.fail_without_output(pattern="bounded output")
        for text in ["", "unknown_architecture\n"]:
            self.f.override = lambda argv: M.CommandResult(argv, 0, text, "") if argv[0].endswith("/lipo") else None
            self.fail_without_output(pattern="architectures")

    def test_changed_executable_or_plist_is_refused_after_commands(self):
        for target in [self.f.exe, self.f.plist]:
            with self.subTest(target=target):
                original = target.read_bytes()
                def change(argv):
                    if argv[0].endswith("/codesign"):
                        target.write_bytes(original + b"changed")
                self.f.override = change
                self.fail_without_output(pattern="changed")
                target.write_bytes(original)

    def test_byte_restore_during_collection_still_breaks_custody_guard(self):
        original = self.f.exe.read_bytes()
        def touch(argv):
            if argv[0].endswith("/codesign"):
                stamp = self.f.exe.stat().st_mtime_ns
                os.utime(self.f.exe, ns=(stamp, stamp + 10_000_000))
        self.f.override = touch
        self.fail_without_output(pattern="changed")
        self.assertEqual(self.f.exe.read_bytes(), original)

    def test_captured_plist_is_parsed_without_late_read_bytes(self):
        observed = []
        original = M.snapshot
        def tracked(path, **kwargs):
            observed.append((path, kwargs.get("capture", False)))
            return original(path, **kwargs)
        with patch.object(M, "snapshot", tracked), patch.object(Path, "read_bytes", side_effect=AssertionError("late read forbidden")):
            _, data, _ = M.collect(self.f.request, runner=self.f.runner)
        self.assertEqual(data["Info_plist"]["CFBundleVersion"], "0.1.0")
        self.assertEqual([capture for path, capture in observed if path == self.f.plist], [True, False])

    def test_oversized_metadata_and_invalid_plist_fail_without_output(self):
        self.f.plist.write_bytes(b"x" * (M.MAX_METADATA_BYTES + 1))
        self.fail_without_output(pattern="bounded size")
        self.f.plist.write_bytes(plistlib.dumps({"CFBundleExecutable": "../../outside"}))
        self.fail_without_output(pattern="basename")
        self.f.plist.write_bytes(b"not a plist")
        self.fail_without_output(pattern="Info.plist")

    def test_legal_plist_date_and_bytes_explicitly_refused_without_output_or_commands(self):
        for value in [datetime.datetime(2026, 10, 6, 11, 0, 0), b"plist data"]:
            with self.subTest(value=value):
                self.f.plist.write_bytes(plistlib.dumps({"CFBundleExecutable": "Fathom", "TypedValue": value}))
                before = self.f.tree()
                self.fail_without_output(pattern="guarded Info.plist")
                self.assertEqual(before, self.f.tree())
        self.assertEqual(self.f.calls, [])

    def test_publication_serializes_both_documents_before_directory_creation(self):
        request, data, readback = M.collect(self.f.request, runner=self.f.runner)
        for target in [data, readback]:
            invalid = dict(target) if isinstance(target, dict) else list(target)
            if isinstance(invalid, dict):
                invalid["unsupported"] = datetime.datetime(2026, 10, 6)
            else:
                invalid.append({"unsupported": b"bytes"})
            with self.subTest(target_type=type(target)), self.assertRaisesRegex(M.AuditError, "Unsupported JSON"):
                M.publish(request, invalid if isinstance(invalid, dict) else data,
                          invalid if isinstance(invalid, list) else readback)
            self.assertFalse(self.f.out.exists())
        with self.assertRaisesRegex(M.AuditError, "bounded document"):
            M.publish(request, {"huge": "x" * M.MAX_OUTPUT_DOCUMENT_BYTES}, readback)
        self.assertFalse(self.f.out.exists())

    def test_failed_publication_reports_incomplete_and_never_success(self):
        request, data, readback = M.collect(self.f.request, runner=self.f.runner)
        real_open = M.os.open
        def fail_leaf(path, *args, **kwargs):
            if path == "current-build-metadata.json":
                raise OSError("synthetic leaf failure")
            return real_open(path, *args, **kwargs)
        with patch.object(M.os, "open", fail_leaf), self.assertRaisesRegex(M.AuditError, "Incomplete owned output"):
            M.publish(request, data, readback)
        self.assertEqual({p.name for p in self.f.out.iterdir()}, {"metadata-command-readback.json"})

    def test_concurrent_output_creation_preserves_other_owner(self):
        request, data, readback = M.collect(self.f.request, runner=self.f.runner)
        self.f.out.mkdir()
        (self.f.out / "other-owner").write_bytes(b"keep")
        with self.assertRaisesRegex(M.AuditError, "fresh"):
            M.publish(request, data, readback)
        self.assertEqual({p.name for p in self.f.out.iterdir()}, {"other-owner"})

    def test_historical_resource_metadata_is_cached_not_resource_access(self):
        historical = self.f.root / "Results/historical-ref.json"
        historical.write_text(json.dumps({"artifact_ref": {"path": "Results/absent-old-manifest.json",
                                                         "bytes": 123, "sha256": "1" * 64},
                                          "resource_sha256": "2" * 64,
                                          "as_of_utc": "2026-10-03T16:00:00Z"}))
        _, data, _ = M.collect(replace(self.f.request, historical_resource_ref=historical), runner=self.f.runner)
        self.assertEqual(len(data["fresh_guarded_input_refs"]), 11)
        self.assertIn("not reread", data["historical_resource_metadata"]["basis"])
        self.assertFalse(data["whole_resources_rehashed"])
        self.assertFalse(data["current_whole_bundle_equality_claim"])
        self.assertFalse((self.f.root / "Results/absent-old-manifest.json").exists())

    def test_historical_ref_rejects_unsafe_or_ambiguous_metadata(self):
        base = {"artifact_ref": {"path": "Results/old.json", "bytes": 12, "sha256": "1" * 64},
                "resource_sha256": "2" * 64, "as_of_utc": "2026-10-03T16:00:00Z"}
        for field, value in [("path", "../escape"), ("path", "/absolute"), ("bytes", True), ("sha256", "bad")]:
            data = json.loads(json.dumps(base))
            data["artifact_ref"][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(M.AuditError):
                M.parse_historical_ref(json.dumps(data).encode())
        base["as_of_utc"] = "2026-10-03T16:00:00"
        with self.assertRaises(M.AuditError):
            M.parse_historical_ref(json.dumps(base).encode())

    def test_macro_values_are_exact_not_substring_or_partial_language_claims(self):
        for value in ["01", "10", "OFF"]:
            parsed = M.parse_compile_definitions(
                f"CXX_DEFINES = -DJUCE_WEB_BROWSER={value} -DJUCE_USE_CURL={value}\n".encode())
            self.assertFalse(parsed["JUCE_curl_explicitly_zero_in_all_observed_groups"])
            self.assertFalse(parsed["JUCE_web_browser_explicitly_zero_in_all_observed_groups"])
        parsed = M.parse_compile_definitions(
            b"CXX_DEFINES = -DJUCE_WEB_BROWSER=0 -DJUCE_USE_CURL=0\nC_DEFINES =\n")
        self.assertFalse(parsed["JUCE_curl_explicitly_zero_in_all_observed_groups"])
        for data in [b"empty", b"CXX_DEFINES = -DJUCE_USE_CURL=0 -DJUCE_USE_CURL=1\n",
                     b"CXX_DEFINES = -DJUCE_USE_CURL=0\nC_DEFINES = -DJUCE_USE_CURL=1\n"]:
            with self.subTest(data=data), self.assertRaises(M.AuditError):
                M.parse_compile_definitions(data)

    def test_empty_signature_display_refuses_inference_or_publication(self):
        self.f.override = lambda argv: M.CommandResult(argv, 0, "", "") if argv[0].endswith("/codesign") else None
        self.fail_without_output(pattern="Missing codesign display")

    def test_main_requires_every_explicit_scope_and_pin_argument(self):
        args = ["--root", str(self.f.root), "--build", str(self.f.build), "--app", str(self.f.app),
                "--expected-executable-sha256", self.f.sha, "--out", str(self.f.out)]
        for index in range(0, len(args), 2):
            with self.subTest(missing=args[index]), patch.object(sys, "stderr"):
                with self.assertRaises(SystemExit) as caught:
                    M.main(args[:index] + args[index + 2:], runner=self.f.runner)
                self.assertEqual(caught.exception.code, 2)
        self.assertFalse(self.f.out.exists())
        self.assertEqual(self.f.calls, [])

    def test_main_explicit_args_publish_only_owned_fresh_directory(self):
        argv = ["--root", str(self.f.root), "--build", str(self.f.build.relative_to(self.f.root)),
                "--app", str(self.f.app.relative_to(self.f.root)), "--expected-executable-sha256", self.f.sha,
                "--out", str(self.f.out.relative_to(self.f.root))]
        with patch("builtins.print"):
            self.assertEqual(M.main(argv, runner=self.f.runner), 0)
        self.assertTrue((self.f.out / "current-build-metadata.json").is_file())
        with patch("builtins.print"):
            self.assertEqual(M.main(argv, runner=self.f.runner), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
