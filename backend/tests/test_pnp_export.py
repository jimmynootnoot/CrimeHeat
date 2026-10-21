"""Shapes specific to the released PNP FOI export.

The export is province-wide, one worksheet per calendar year, names offences by
their statute, and — for every year but one — supplies a time of day with no
incident date at all. Each of those is covered here.
"""
import datetime
import io
import json
import unittest

import pandas as pd

from app.core.taxonomy import CANONICAL_MUNICIPALITIES, normalize_crime_type
from app.services.import_service import parse_file, suggest_mapping, validate_rows

MUNICIPALITIES = set(CANONICAL_MUNICIPALITIES)

DATED = ["blotterno", "municipal", "barangay", "dateCommitted", "offense", "lat", "lng"]
TIMED = ["blotterno", "municipal", "barangay", "timeCommitted", "offense", "lat", "lng"]
REPORTED = ["blotterno", "municipal", "barangay", "timeReported", "offense", "lat", "lng"]
EXTRA = ["blotterno", "municipal", "barangay", "timeCommitted", "stageoffelony",
         "offense", "lat", "lng"]


def workbook(sheets: dict[str, list[list]]) -> bytes:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer) as writer:
        for name, rows in sheets.items():
            pd.DataFrame(rows).to_excel(writer, sheet_name=name, index=False, header=False)
    return buffer.getvalue()


def run(content: bytes):
    frame, notes = parse_file("foi.xlsx", content)
    rows = json.loads(frame.to_json(orient="records", date_format="iso"))
    mapping = suggest_mapping(list(frame.columns.astype(str)))
    valid, issues, fixes = validate_rows(rows, mapping, MUNICIPALITIES, id_prefix="B1")
    return valid, issues, fixes, notes, mapping


class PnpExportTests(unittest.TestCase):
    def test_statute_offence_names_map_to_index_crimes(self):
        cases = {
            "THEFT  - RPC Art. 308": "Theft",
            "QUALIFIED THEFT  - RPC Art. 310  as amended by BP Blg 71": "Theft",
            "HOMICIDE  - RPC Art. 249": "Homicide",
            "MURDER  - RPC Art. 248": "Murder",
            "SERIOUS PHYSICAL INJURIES  - RPC Art. 263": "Physical Injury",
            "SLIGHT PHYSICAL INJURIES AND MALTREATMENT  - RPC Art. 266": "Physical Injury",
            "ANTI-RAPE LAW OF 1997 - RA 8353": "Rape",
            "RAPE - RPC Art 266-A": "Rape",
            "ROBBERY  - RPC Art. 293": "Robbery",
            "NEW ANTI-CARNAPPING ACT OF 2016 - MC - RA 10883 (repealed RA 6539)": "Carnapping",
            "ANTI-CATTLE RUSTLING LAW OF 1974 - PD 533": "Cattle Rustling",
        }
        for offence, expected in cases.items():
            with self.subTest(offence=offence):
                self.assertEqual(normalize_crime_type(offence)[0], expected)

    def test_special_complex_crimes_take_their_principal_offence(self):
        """Robbery with Homicide is a robbery (RPC Art. 294) and Rape with
        Homicide a rape (Art. 266-B); filing either under Homicide would
        overstate the homicide series and understate the other."""
        self.assertEqual(normalize_crime_type("ROBBERY WITH HOMICIDE - RPC Art. 294")[0], "Robbery")
        self.assertEqual(normalize_crime_type("RAPE WITH HOMICIDE - RPC Art. 266-B")[0], "Rape")
        self.assertEqual(
            normalize_crime_type("ROBBERY WITH SERIOUS PHYSICAL INJURIES - RPC Art. 294")[0],
            "Robbery",
        )

    def test_quasi_offences_are_not_index_crimes(self):
        """RPC Art. 365 negligence cases are counted separately by the PNP;
        matching the crime word inside them would inflate the real series."""
        for offence in (
            "RECKLESS IMPRUDENCE RESULTING TO HOMICIDE - RPC Art 365",
            "RECKLESS IMPRUDENCE RESULTING TO PHYSICAL INJURY - RPC Art 365",
            "RECKLESS IMPRUDENCE RESULTING TO DAMAGE TO PROPERTY - RPC Art 365",
            "ACTS OF LASCIVIOUSNESS  - RPC Art. 336",
            "COMPREHENSIVE DANGEROUS DRUGS ACT OF 2002  - RA 9165",
            "ANTI-GAMBLING LAW - PD 1602",
            "PARRICIDE  - RPC Art. 246",
        ):
            with self.subTest(offence=offence):
                self.assertIsNone(normalize_crime_type(offence)[0])

    def test_year_only_sheets_are_dated_from_the_tab_name(self):
        content = workbook({
            "CY 2018": [TIMED,
                        ["124705-201801-0001", "LIBUNGAN", "MONTAY", "19:00:00",
                         "THEFT  - RPC Art. 308", "7.282274", "124.551147"]],
        })
        valid, issues, fixes, _, _ = run(content)
        self.assertEqual(len(valid), 1)
        self.assertEqual(valid[0]["incident_date"], "2018-01-01")
        self.assertEqual(valid[0]["date_precision"], "year_only")
        self.assertTrue([f for f in fixes if f["field"] == "incident_date"],
                        "a date inferred from the tab name must be reported")
        self.assertFalse([i for i in issues if i["severity"] == "rejected"])

    def test_a_real_date_column_keeps_exact_precision(self):
        content = workbook({
            "CY 2021": [DATED,
                        ["124705-202101-0001", "LIBUNGAN", "MONTAY", "2021-03-17",
                         "MURDER  - RPC Art. 248", "7.282274", "124.551147"]],
        })
        valid, _, _, _, _ = run(content)
        self.assertEqual(valid[0]["incident_date"], "2021-03-17")
        self.assertEqual(valid[0]["date_precision"], "exact")

    def test_year_tabs_with_drifting_headers_all_combine(self):
        """A renamed date column or an extra column in a single year must not
        silently drop that year from the dataset."""
        content = workbook({
            "CY 2021": [DATED, ["A-1", "LIBUNGAN", "MONTAY", "2021-03-17",
                                "THEFT  - RPC Art. 308", "7.282274", "124.551147"]],
            "CY 2022": [TIMED, ["A-2", "LIBUNGAN", "MONTAY", "19:00:00",
                                "THEFT  - RPC Art. 308", "7.282274", "124.551147"]],
            "CY 2024": [REPORTED, ["A-3", "LIBUNGAN", "MONTAY", "08:00:00",
                                   "THEFT  - RPC Art. 308", "7.282274", "124.551147"]],
            "CY 2018": [EXTRA, ["A-4", "LIBUNGAN", "MONTAY", "19:00:00", "CONSUMMATED",
                                "THEFT  - RPC Art. 308", "7.282274", "124.551147"]],
        })
        valid, _, _, notes, _ = run(content)
        self.assertEqual(len(valid), 4, "every year tab must survive the merge")
        self.assertEqual(
            sorted(v["incident_date"] for v in valid),
            ["2018-01-01", "2021-03-17", "2022-01-01", "2024-01-01"],
        )
        self.assertTrue(any("aligned by column name" in n for n in notes))

    def test_out_of_area_and_non_index_rows_are_rejected_not_imported(self):
        content = workbook({
            "CY 2021": [DATED,
                        ["A-1", "CITY OF KIDAPAWAN (CAPITAL)", "SUDAPIN", "2021-01-01",
                         "MURDER  - RPC Art. 248", "7.025243", "125.096794"],
                        ["A-2", "LIBUNGAN", "MONTAY", "2021-01-02",
                         "COMPREHENSIVE DANGEROUS DRUGS ACT OF 2002  - RA 9165",
                         "7.282274", "124.551147"],
                        ["A-3", "PIGKAWAYAN", "MIDPAPAN II", "2021-01-03",
                         "THEFT  - RPC Art. 308", "7.298609", "124.430359"]],
        })
        valid, issues, _, _, _ = run(content)
        self.assertEqual([v["incident_id"] for v in valid], ["A-3"])
        self.assertEqual(valid[0]["municipality"], "Pigcawayan")
        fields = {i["field"] for i in issues if i["severity"] == "rejected"}
        self.assertEqual(fields, {"municipality", "crime_type"})

    def test_export_headers_are_auto_mapped(self):
        for header in (DATED, TIMED, REPORTED, EXTRA):
            with self.subTest(date_column=header[3]):
                mapping = suggest_mapping(header)
                self.assertEqual(mapping["incident_id"], "blotterno")
                self.assertEqual(mapping["municipality"], "municipal")
                self.assertEqual(mapping["crime_type"], "offense")
                self.assertEqual(mapping["longitude"], "lng")

    def test_phantom_formatting_rows_do_not_become_records(self):
        rows = [TIMED, ["A-1", "LIBUNGAN", "MONTAY", "19:00:00",
                        "THEFT  - RPC Art. 308", "7.282274", "124.551147"]]
        rows += [[None] * 7 for _ in range(900)]  # formatting-only tail
        frame, _ = parse_file("foi.xlsx", workbook({"CY 2020": rows}))
        self.assertEqual(len(frame), 1)


if __name__ == "__main__":
    unittest.main()
