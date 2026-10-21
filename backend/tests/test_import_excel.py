"""Worksheet (.xlsx) imports.

Excel stores dates, times and numbers as typed cells rather than text, and PNP
exports commonly carry a title block above the header and one tab per year.
These are the failure modes a CSV never exhibits, so they are covered here.
"""
import datetime
import io
import json
import unittest

import pandas as pd

from app.core.taxonomy import CANONICAL_MUNICIPALITIES
from app.services.import_service import (
    SHEET_COLUMN,
    parse_file,
    suggest_mapping,
    validate_rows,
)

MUNICIPALITIES = set(CANONICAL_MUNICIPALITIES)

HEADERS = [
    "Blotter Entry No", "Nature of Offense", "Date Committed", "Time Committed",
    "City/Municipality", "Brgy", "Lat", "Long",
]


def incident(entry="BLT-001", day=datetime.date(2023, 12, 25)):
    return [entry, "Theft", day, datetime.time(14, 30), "Pikit", "Balabak", 7.122, 124.719]


def workbook(sheets: dict[str, list[list]]) -> bytes:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer) as writer:
        for name, rows in sheets.items():
            pd.DataFrame(rows).to_excel(writer, sheet_name=name, index=False, header=False)
    return buffer.getvalue()


def data_columns(frame):
    """Columns excluding the reader's reserved worksheet-name column."""
    return [c for c in frame.columns.astype(str) if c != SHEET_COLUMN]


def import_workbook(content: bytes, filename="pnp_export.xlsx"):
    frame, notes = parse_file(filename, content)
    # Mirrors the upload route: the batch is persisted as JSON before validation.
    rows = json.loads(frame.to_json(orient="records", date_format="iso"))
    mapping = suggest_mapping(list(frame.columns.astype(str)))
    valid, issues, fixes = validate_rows(rows, mapping, MUNICIPALITIES, id_prefix="B1")
    return valid, issues, fixes, notes


class ExcelImportTests(unittest.TestCase):
    def test_real_date_cells_survive_the_json_round_trip(self):
        valid, issues, _, _ = import_workbook(workbook({"Sheet1": [HEADERS, incident()]}))
        self.assertEqual([i for i in issues if i["severity"] == "rejected"], [])
        self.assertEqual(len(valid), 1)
        self.assertEqual(valid[0]["incident_date"], "2023-12-25")
        self.assertEqual(valid[0]["incident_time"], "14:30")

    def test_title_block_above_the_header_is_skipped(self):
        content = workbook({"Sheet1": [
            ["Republic of the Philippines", None, None, None, None, None, None, None],
            ["PNP Cotabato Provincial Office", None, None, None, None, None, None, None],
            [None, None, None, None, None, None, None, None],
            HEADERS,
            incident(),
        ]})
        frame, _ = parse_file("pnp_export.xlsx", content)
        self.assertEqual(data_columns(frame), HEADERS)
        valid, issues, _, _ = import_workbook(content)
        self.assertEqual([i for i in issues if i["severity"] == "rejected"], [])
        self.assertEqual(len(valid), 1)

    def test_per_year_tabs_are_combined(self):
        content = workbook({
            "2023": [HEADERS, incident("BLT-001", datetime.date(2023, 5, 1))],
            "2024": [HEADERS, incident("BLT-002", datetime.date(2024, 5, 1))],
        })
        valid, _, _, notes = import_workbook(content)
        self.assertEqual(len(valid), 2)
        self.assertEqual(
            sorted(v["incident_date"] for v in valid), ["2023-05-01", "2024-05-01"]
        )
        self.assertTrue(any("combined" in n for n in notes))

    def test_sheet_with_different_columns_is_skipped_and_reported(self):
        content = workbook({
            "Incidents": [HEADERS, incident()],
            "Legend": [["Code", "Meaning"], ["IDX", "Index crime"]],
        })
        valid, _, _, notes = import_workbook(content)
        self.assertEqual(len(valid), 1)
        self.assertTrue(any("skipped" in n and "Legend" in n for n in notes))

    def test_text_dates_in_a_worksheet_still_detect_day_first(self):
        content = workbook({"Sheet1": [
            HEADERS,
            ["BLT-001", "Theft", "25/12/2023", "14:30", "Pikit", "Balabak", 7.122, 124.719],
            ["BLT-002", "Theft", "05/03/2023", "09:00", "Pikit", "Balabak", 7.122, 124.719],
        ]})
        valid, _, _, _ = import_workbook(content)
        self.assertEqual(
            [v["incident_date"] for v in valid], ["2023-12-25", "2023-03-05"]
        )

    def test_blank_trailing_rows_are_dropped(self):
        content = workbook({"Sheet1": [
            HEADERS,
            incident(),
            [None] * len(HEADERS),
            [None] * len(HEADERS),
        ]})
        frame, _ = parse_file("pnp_export.xlsx", content)
        self.assertEqual(len(frame), 1)

    def test_extensions_that_lie_about_the_format_are_still_read(self):
        """A record system's .xls is often a real .xlsx, an HTML table, or
        delimited text. The reader tries every applicable format."""
        real_xlsx = workbook({"Sheet1": [HEADERS, incident()]})
        row = ["BLT-001", "Theft", "2023-12-25", "14:30", "Pikit", "Balabak", "7.122", "124.719"]
        html = "<html><table>" + "".join(
            "<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in (HEADERS, row)
        ) + "</table></html>"

        for label, name, content in [
            ("xlsx named .xls", "f.xls", real_xlsx),
            ("html named .xls", "f.xls", html.encode()),
            ("tsv named .xls", "f.xls", ("\t".join(HEADERS) + "\n" + "\t".join(row)).encode()),
        ]:
            with self.subTest(label=label):
                frame, _ = parse_file(name, content)
                self.assertEqual(len(frame), 1)
                self.assertEqual(data_columns(frame), HEADERS)

    def test_delimiters_and_encodings_are_detected(self):
        row = ["BLT-001", "Theft", "2023-12-25", "14:30", "Pikit", "Bañado", "7.122", "124.719"]
        for label, delimiter, encoding in [
            ("comma utf-8-sig", ",", "utf-8-sig"),
            ("semicolon latin-1", ";", "latin-1"),
            ("tab utf-8", "\t", "utf-8"),
            ("pipe cp1252", "|", "cp1252"),
        ]:
            with self.subTest(label=label):
                text = delimiter.join(HEADERS) + "\n" + delimiter.join(row)
                frame, _ = parse_file("f.csv", text.encode(encoding))
                self.assertEqual(len(frame), 1)
                self.assertEqual(data_columns(frame), HEADERS)

    def test_csv_title_block_above_the_header_is_skipped(self):
        row = ["BLT-001", "Theft", "2023-12-25", "14:30", "Pikit", "Balabak", "7.122", "124.719"]
        text = (
            "PNP Cotabato Provincial Office\n"
            "\n"
            + ",".join(HEADERS) + "\n"
            + ",".join(row) + "\n"
        )
        frame, _ = parse_file("f.csv", text.encode())
        self.assertEqual(data_columns(frame), HEADERS)
        self.assertEqual(len(frame), 1)

    def test_unreadable_content_raises_an_actionable_error(self):
        for label, name, content in [
            ("garbage", "f.xlsx", b"\x00\x01\x02not a spreadsheet"),
            ("empty", "f.csv", b""),
        ]:
            with self.subTest(label=label):
                with self.assertRaises(ValueError):
                    parse_file(name, content)

    def test_csv_path_still_works_and_returns_no_notes(self):
        csv = (
            "Blotter Entry No,Nature of Offense,Date Committed,City/Municipality,Brgy,Lat,Long\n"
            "BLT-001,Theft,2023-12-25,Pikit,Balabak,7.122,124.719\n"
        )
        frame, notes = parse_file("export.csv", csv.encode())
        self.assertEqual(notes, [])
        valid, _, _, _ = import_workbook(csv.encode(), filename="export.csv")
        self.assertEqual(valid[0]["incident_date"], "2023-12-25")


if __name__ == "__main__":
    unittest.main()
