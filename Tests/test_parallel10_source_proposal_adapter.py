"""Focused whole-Level7 source-to-proposal and refusal checks."""

from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from Tools import parallel10_source_proposal_adapter as subject


class Level7ProposalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.aggregate, cls.context = subject.read_inputs()
        cls.proposal = subject.build_proposal(cls.aggregate, cls.context, subject.Level7Adapter())

    def test_complete_unallocated_corpus_and_source_contacts(self) -> None:
        output = self.proposal
        self.assertEqual(output["schema1_contract_version"], "1.0.0-curriculum-candidate")
        self.assertEqual(output["coverage"]["record_count"], 108)
        self.assertEqual(output["coverage"]["route_count"], 432)
        self.assertEqual(output["coverage"]["contact_count"], 1728)
        self.assertFalse(output["coverage"]["whole_workbook_complete"])
        self.assertEqual(len(output["set_guidance"]), 9)
        self.assertEqual(output["authority"], {"canonical_ids_allocated": False, "runtime_eligible": False,
                                              "imported": False, "admitted": False, "native_schema1_package": False})
        keys = [r["source_local_key"] for r in output["records"]]
        self.assertEqual(len(keys), len(set(keys)))
        for index, (source, proposed) in enumerate(zip(self.aggregate["records"], output["records"], strict=True)):
            self.assertEqual(proposed["source_local_key"], f"L7-set{index // 12 + 1:02d}-ex{index + 1:03d}")
            self.assertEqual(proposed["source_record_sha256"], subject.value_sha(source))
            self.assertEqual(proposed["source_refs"], source["source_refs"])
            record = proposed["record_proposal"]
            self.assertIsNone(record["id"])
            self.assertIsNone(record["workbook_id"])
            self.assertIsNone(record["module_id"])
            self.assertIsNone(record["content_revision"])
            self.assertIsNone(record["lineage"])
            self.assertEqual(record["variants"], [])
            self.assertEqual(len(record["route_proposals"]), 4)
            self.assertEqual(len(record["events"]), 16)
            self.assertEqual(record["timing"], {"status": "unresolved", "unit": None,
                                                "fixed_bpm": None, "note_per_click": None})
            source_routes = [route for direction in source["directions"] for route in direction["routes"]]
            for route_number, (raw_route, route) in enumerate(zip(source_routes, record["route_proposals"], strict=True)):
                self.assertEqual(route["played_strings"], raw_route["strings"])
                self.assertEqual(route["silent_intervening_strings"], 2)
                self.assertEqual(len(route["source_occurrence_keys"]), 4)
                for raw_note, event in zip(raw_route["notes"], record["events"][route_number * 4:(route_number + 1) * 4], strict=True):
                    string_number, open_pitch = subject.OPEN_MIDI[raw_note["string"]]
                    self.assertEqual((event["string"], event["fret"], event["finger"], event["midi"]),
                                     (string_number, raw_note["fret"], int(raw_note["finger_digit"]), open_pitch + raw_note["fret"]))
                    self.assertIsNone(event["event_id"])
                    self.assertIsNone(event["onset_q"])
                    self.assertIsNone(event["duration_q"])
                    self.assertIsNone(event["attack"])

    def test_original_txt_pdf_and_catalog_are_bound(self) -> None:
        self.assertEqual(len(self.context.pdf_cards), 108)
        for number, row in enumerate(self.aggregate["records"], 1):
            page, code, rows = self.context.pdf_cards[number]
            self.assertEqual((page, code), (number // 12 + (1 if number % 12 else 0) + 1, row["code"]))
            self.assertEqual(rows, row["directions"][0]["tab_rows"] + row["directions"][1]["tab_rows"])
        self.assertEqual(self.proposal["source_catalog_workbook_id"], "fg:workbook:000007")
        self.assertEqual(self.proposal["input_sha256"][str(subject.TXT)], subject.PINS[subject.TXT])
        self.assertEqual(self.proposal["input_sha256"][str(subject.PDF)], subject.PINS[subject.PDF])

    def test_duplicate_key_and_wrong_source_semantics_refuse(self) -> None:
        broken = copy.deepcopy(self.aggregate)
        broken["records"][1]["source_local_key"] = broken["records"][0]["source_local_key"]
        with self.assertRaisesRegex(subject.ProposalError, "DUPLICATE_SOURCE_LOCAL_KEY"):
            subject.build_proposal(broken, self.context, subject.Level7Adapter())
        for mutate, code in (
            (lambda x: x["records"][0]["directions"][0]["routes"][0]["notes"][0].update(fret=8), "SOURCE_NOTE"),
            (lambda x: x["records"][0]["directions"][0]["tab_rows"].__setitem__(0, "e|invented|"), "TAB_SOURCE_FIDELITY"),
            (lambda x: x["records"][0].update(code="9999"), "FINGER_CODE"),
            (lambda x: x["records"][0].update(onset_q=[0, 1]), "INVENTED_ID_OR_TIMING"),
            (lambda x: x["records"][0].update(canonical_item_id="fg:item:999999"), "INVENTED_ID_OR_TIMING"),
            (lambda x: x["records"][0].update(runtime_eligible=True), "INVALID_ADMISSION"),
        ):
            with self.subTest(code=code):
                broken = copy.deepcopy(self.aggregate)
                mutate(broken)
                with self.assertRaisesRegex(subject.ProposalError, code):
                    subject.build_proposal(broken, self.context, subject.Level7Adapter())

    def test_pinned_source_drift_refuses_before_output(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for rel in subject.PINS:
                path = root / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                if rel == subject.TXT:
                    path.write_bytes((subject.ROOT / rel).read_bytes() + b"\ncorruption")
                else:
                    path.symlink_to(subject.ROOT / rel)
            with self.assertRaisesRegex(subject.ProposalError, "PIN_DRIFT"):
                subject.read_inputs(root)

    def test_reusable_core_accepts_another_shape_without_level7_rules(self) -> None:
        class ToyAdapter:
            name = "toy.1"
            wbs_id = "toy"
            level = 99
            expected_records = 2
            expected_routes = 0
            expected_contacts = 0
            gaps = ("Toy authority remains unset.",)

            def check_aggregate(self, aggregate, context):
                subject.require(aggregate["level"] == 99, "TOY_LEVEL")

            def expected_key(self, index):
                return f"toy-{index + 1}"

            def normalize(self, row, index, context):
                return {"source_local_key": row["source_local_key"],
                        "record_proposal": {"route_proposals": [], "events": []}}

            def guidance(self, aggregate):
                return []

        base = {**{key: None for key in subject.NULL_FIELDS}, **{key: False for key in subject.FALSE_FIELDS}}
        aggregate = {"level": 99, "records": [{**base, "source_local_key": "toy-1"},
                                               {**base, "source_local_key": "toy-2"}], "set_provenance": []}
        result = subject.build_proposal(aggregate, self.context, ToyAdapter())
        self.assertEqual(result["coverage"]["record_count"], 2)
        self.assertEqual(result["adapter"], "toy.1")

    def test_deterministic_twin_and_output_refusals(self) -> None:
        (subject.ROOT / subject.OUT).mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=subject.ROOT / subject.OUT) as folder:
            base = Path(folder)
            first, second = base / "first.json", base / "second.json"
            size_a, hash_a = subject.write_proposal(first)
            size_b, hash_b = subject.write_proposal(second)
            self.assertEqual((size_a, hash_a), (size_b, hash_b))
            self.assertEqual(first.read_bytes(), second.read_bytes())
            self.assertEqual(json.loads(first.read_text()), self.proposal)
            with self.assertRaisesRegex(subject.ProposalError, "OUTPUT_EXISTS_OR_SYMLINK"):
                subject.write_proposal(first)
            link = base / "link.json"
            link.symlink_to(first)
            with self.assertRaisesRegex(subject.ProposalError, "OUTPUT_EXISTS_OR_SYMLINK"):
                subject.write_proposal(link)
            with self.assertRaisesRegex(subject.ProposalError, "OUTPUT_OUTSIDE_BUILD"):
                subject.write_proposal(subject.ROOT / "Results/parallel-10/admission/forbidden.json")


if __name__ == "__main__":
    unittest.main()
