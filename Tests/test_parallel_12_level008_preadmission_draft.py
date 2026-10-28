"""Whole-Level 8 noncanonical draft structure and fail-closed boundaries."""

from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from parallel_12_level008_preadmission_draft import (
    AGGREGATE, AGGREGATE_PIN, COUNTS, ROOT, DraftError, build, load_pinned,
    materialize, serialize, write_output,
)
from parallel_12_level008_sets01_09_normalize import digest, verify


class PreadmissionDraftTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.aggregate = load_pinned(ROOT)

    def change(self, mutate, expected: str) -> None:
        document = copy.deepcopy(self.aggregate)
        mutate(document)
        with self.assertRaisesRegex(DraftError, expected):
            materialize(document)

    def test_whole_level_counts_order_and_nonadmission(self) -> None:
        draft = materialize(self.aggregate)
        self.assertEqual(draft["classification"], "noncanonical_nonadmitted_structural_draft")
        self.assertEqual(draft["counts"], COUNTS)
        self.assertEqual(len(draft["records"]), 108)
        self.assertEqual([record["exercise_number"] for record in draft["records"]],
                         [f"{number:03d}" for number in range(1, 109)])
        self.assertEqual([record["source_local_key"] for record in draft["records"]],
                         [f"L8-set{(number - 1) // 12 + 1:02d}-ex{number:03d}" for number in range(1, 109)])
        for record in draft["records"]:
            self.assertEqual(len(record["directions"]), 2)
            self.assertEqual(record["source_refs"]["pdf"], f"L8-PDF1-p{record['set'] + 1}")
            self.assertIsNone(record["canonical_item_id"])
            self.assertIsNone(record["canonical_variant_id"])
            self.assertIsNone(record["onset_q"])
            self.assertIsNone(record["duration_q"])
            self.assertIsNone(record["fixed_bpm"])
            self.assertIsNone(record["note_per_click"])
            self.assertFalse(record["runtime_eligible"] or record["runtime_admitted"] or
                             record["imported"] or record["admitted"])
            for direction in record["directions"]:
                self.assertEqual(len(direction["routes"]), 6)
                self.assertEqual([route["string"] for route in direction["routes"]], direction["route_order"])
                for route_index, route in enumerate(direction["routes"]):
                    self.assertEqual(len(route["ordered_notes"]), 8)
                    self.assertEqual(route["shift_after_cell"], 1)
                    self.assertTrue(route["shift_at_center_barline"])
                    self.assertEqual([note["source_sequence_ordinal"] for note in route["ordered_notes"]],
                                     list(range(route_index * 8 + 1, route_index * 8 + 9)))
                    self.assertEqual([note["route_note_ordinal"] for note in route["ordered_notes"]],
                                     list(range(1, 9)))
                    self.assertEqual([note["cell_ordinal"] for note in route["ordered_notes"]],
                                     [1] * 4 + [2] * 4)
                    self.assertTrue(all(note["onset_q"] is None and note["duration_q"] is None
                                        for note in route["ordered_notes"]))
        self.assertFalse(draft["whole_workbook_complete"])

    def test_every_materialized_note_round_trips_to_normalized_source(self) -> None:
        draft = materialize(self.aggregate)
        for source_record, output_record in zip(self.aggregate["records"], draft["records"], strict=True):
            self.assertEqual(output_record["source_refs"], source_record["source_refs"])
            for source_direction, output_direction in zip(source_record["directions"], output_record["directions"], strict=True):
                self.assertEqual(output_direction["printed_tab_rows_high_to_low"],
                                 source_direction["printed_tab_rows_high_to_low"])
                self.assertEqual(output_direction["pdf_template"], source_direction["pdf_template"])
                for source_route, output_route in zip(source_direction["routes"], output_direction["routes"], strict=True):
                    self.assertEqual(output_route["printed_tab_row"], source_route["printed_tab_row"])
                    original = [note for cell in source_route["cells"] for note in cell["notes"]]
                    for source_note, output_note in zip(original, output_route["ordered_notes"], strict=True):
                        for field in ("string", "position", "fret", "finger_digit", "finger_name",
                                      "ascii_column", "onset_q", "duration_q"):
                            self.assertEqual(output_note[field], source_note[field])

    def test_pinned_aggregate_and_all_sources_are_rechecked(self) -> None:
        data = (ROOT / AGGREGATE).read_bytes()
        verify(data, AGGREGATE_PIN, "R02_AGGREGATE")
        with self.assertRaisesRegex(ValueError, "PINNED_INPUT_DRIFT"):
            verify(data + b"x", AGGREGATE_PIN, "R02_AGGREGATE")
        self.assertEqual(build(), materialize(self.aggregate))
        self.assertEqual(digest(data), AGGREGATE_PIN[1])
        self.assertEqual(json.loads(serialize(build()))["records"][-1]["exercise_number"], "108")

    def test_deterministic_serialization_and_output_boundary(self) -> None:
        self.assertEqual(serialize(build()), serialize(build()))
        with self.assertRaisesRegex(DraftError, "OUTPUT_BOUNDARY"):
            write_output(Path("relative-draft.json"), b"{}")
        with self.assertRaisesRegex(DraftError, "OUTPUT_BOUNDARY"):
            write_output(ROOT / "Build/parallel-12/other/draft.json", b"{}")

    def test_route_note_and_schema_loss_refuse(self) -> None:
        self.change(lambda d: d["records"][71]["directions"][0]["routes"].pop(), "ROUTE_LOSS_OR_ORDER")
        self.change(lambda d: d["records"][95]["directions"][1]["routes"][2]["cells"][1]["notes"].pop(),
                    "CELL_LOSS")
        self.change(lambda d: d["records"][0]["directions"][0]["routes"][0]["cells"][0]["notes"][0].update(unexpected="loss"),
                    "SCHEMA_CHANGE")
        self.change(lambda d: d["records"][0]["directions"][0]["routes"][0]["cells"][0]["notes"][0].update(fret=99),
                    "NOTE_LOSS_OR_CHANGE")
        self.change(lambda d: d["records"][0]["directions"][0]["routes"][0].update(shift_after_cell=2),
                    "ROUTE_OR_SHIFT")

    def test_duplicate_source_identity_and_false_admission_refuse(self) -> None:
        self.change(lambda d: d["records"][1].update(source_local_key=d["records"][0]["source_local_key"]),
                    "SOURCE_LOCAL_ORDER")
        self.change(lambda d: d["records"][107].update(canonical_item_id="invented"), "FALSE_ID_OR_TIME")
        self.change(lambda d: d["records"][107].update(onset_q=[0, 1]), "FALSE_ID_OR_TIME")
        self.change(lambda d: d.update(runtime_admitted=True), "FALSE_ADMISSION")
        self.change(lambda d: d["set_metadata"][2].update(candidate_sha256="0" * 64),
                    "SET_SOURCE_IDENTITY")


if __name__ == "__main__":
    unittest.main()
