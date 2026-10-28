"""Focused exact-contract checks for the detached Level 8 Sets 1–5 adapter."""

from __future__ import annotations

import copy
import json
import unittest

from parallel_12_level008_sets01_05_normalize import (
    CANDIDATES, PDF, ROOT, SOURCE_PINS, TXT, NormalizeError, build,
    load_pinned, normalize_documents, serialize, verify,
)


class LevelEightNormalizationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.documents, cls.txt, cls.pdf = load_pinned(ROOT)

    def mutate(self, change, code: str) -> None:
        documents = copy.deepcopy(self.documents)
        change(documents)
        with self.assertRaisesRegex(NormalizeError, code):
            normalize_documents(documents, self.txt, self.pdf)

    def test_all_five_sets_and_every_route_survive_without_admission(self) -> None:
        result = normalize_documents(self.documents, self.txt, self.pdf)
        self.assertEqual(result["sets"], [1, 2, 3, 4, 5])
        self.assertEqual(result["counts"], {"records": 60, "directions": 120, "string_routes": 720,
                                            "four_note_cells": 1440, "untimed_note_projections": 5760})
        self.assertEqual(len(result["records"]), 60)
        self.assertEqual(len({record["source_local_key"] for record in result["records"]}), 60)
        self.assertEqual([record["exercise_number"] for record in result["records"]],
                         [f"{number:03d}" for number in range(1, 61)])
        for record in result["records"]:
            self.assertEqual(record["source_refs"]["pdf"], f"L8-PDF1-p{record['set'] + 1}")
            self.assertIsNone(record["canonical_item_id"])
            self.assertIsNone(record["canonical_variant_id"])
            self.assertIsNone(record["onset_q"])
            self.assertIsNone(record["duration_q"])
            self.assertFalse(record["admitted"] or record["runtime_admitted"] or record["runtime_eligible"])
            self.assertEqual([direction["direction"] for direction in record["directions"]],
                             ["shift_up", "shift_down"])
            for direction in record["directions"]:
                self.assertEqual(len(direction["routes"]), 6)
                self.assertEqual([route["string"] for route in direction["routes"]], direction["route_order"])
                for route in direction["routes"]:
                    self.assertEqual(len(route["cells"]), 2)
                    self.assertEqual([len(cell["notes"]) for cell in route["cells"]], [4, 4])
                    self.assertEqual(route["shift_after_cell"], 1)
                    self.assertTrue(route["shift_at_center_barline"])
                    self.assertEqual(route["hand_frame_shift_frets"],
                                     2 if direction["direction"] == "shift_up" else -2)
                    for cell in route["cells"]:
                        self.assertTrue(all(note["onset_q"] is None and note["duration_q"] is None
                                            for note in cell["notes"]))
        self.assertFalse(result["whole_workbook_complete"])
        self.assertEqual(result["classification"], "detached_non_admitted_candidate")

    def test_pinned_inputs_and_deterministic_serialization(self) -> None:
        self.assertEqual(build(), normalize_documents(self.documents, self.txt, self.pdf))
        first = serialize(build())
        second = serialize(build())
        self.assertEqual(first, second)
        self.assertEqual(json.loads(first)["records"][0]["source_local_key"], "L8-set01-ex001")
        self.assertEqual(json.loads(first)["records"][-1]["source_local_key"], "L8-set05-ex060")
        for path, pin in SOURCE_PINS.items():
            data = (ROOT / path).read_bytes()
            verify(data, pin, path.name)
            with self.assertRaisesRegex(NormalizeError, "PINNED_INPUT_DRIFT"):
                verify(data + b"x", pin, path.name)
        for number, (path, size, sha) in CANDIDATES.items():
            data = (ROOT / path).read_bytes()
            verify(data, (size, sha), f"SET{number}")
            with self.assertRaisesRegex(NormalizeError, "PINNED_INPUT_DRIFT"):
                verify(data[:-1], (size, sha), f"SET{number}")
        self.assertEqual(SOURCE_PINS[TXT][0], 53407)
        self.assertEqual(SOURCE_PINS[PDF][0], 43123)

    def test_duplicate_exercise_key_and_record_loss_refuse(self) -> None:
        self.mutate(lambda d: d[2]["records"][0].update(source_local_key=d[1]["records"][0]["source_local_key"]),
                    "DUPLICATE_EXERCISE_KEY")
        self.mutate(lambda d: d[3]["records"].pop(), "RECORD_COUNT")

    def test_route_loss_and_mixed_schema_refuse(self) -> None:
        self.mutate(lambda d: d[4]["records"][0]["directions"][0]["routes"].pop(), "ROUTE_LOSS")
        self.mutate(lambda d: d[2]["records"][0]["directions"][0].update(routes=[]), "FIELD_SHAPE")
        self.mutate(lambda d: d[3]["records"][0]["directions"][0]["string_routes"][0].update(string="A"),
                    "ROUTE_LOSS_OR_ORDER")

    def test_shift_cell_finger_and_printed_tab_refuse(self) -> None:
        self.mutate(lambda d: d[1]["records"][0]["directions"][0]["routes"][0].update(shift_after_cell=0),
                    "SHIFT_BOUNDARY")
        self.mutate(lambda d: d[5]["records"][0]["directions"][0]["string_routes"][0]["cells"][1]["notes"][0].update(fret=99),
                    "NOTE_SEMANTICS")
        self.mutate(lambda d: d[4]["records"][0]["directions"][0]["txt_tab_rows_high_to_low"].__setitem__(0, "e|0|0|"),
                    "TXT_TAB_REF|PDF_TXT_TEMPLATE")

    def test_source_ref_and_false_admission_refuse(self) -> None:
        self.mutate(lambda d: d[3]["records"][0]["source_refs"].update(txt="L8-TXT1-1-15"),
                    "TXT_LINE_REF")
        self.mutate(lambda d: d[1].update(runtime_admitted=True), "FALSE_ADMISSION")
        self.mutate(lambda d: d[5]["records"][0].update(canonical_item_id="invented"),
                    "INVENTED_ID_OR_TIME")
        self.mutate(lambda d: d[2]["records"][0]["directions"][0]["string_routes"][0]["cells"][0]["notes"][0].update(onset_q=[0, 1]),
                    "NOTE_SEMANTICS")


if __name__ == "__main__":
    unittest.main()
