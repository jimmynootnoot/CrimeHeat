# Evaluation export

Open **Reports → Evaluation export (90% / 10%)**. Supply three CSV files:

- System predictions: `unit_id,predicted_label`
- Independently validated reference classification: `unit_id,reference_label`
- Functional test outcomes: `case_code,status`

Labels are binary: `1` means hotspot and `0` means non-hotspot. The prediction
and reference files must contain exactly the same unique unit IDs, including
negative units. Define the unit (for example, a fixed grid cell), dataset/run,
period, and geographic coverage in the scope field. Do not derive reference
labels from the predictions being evaluated. Record the validator and evidence
identifier; selecting a source does not independently certify its validation.
Synthetic references must use the synthetic demonstration option.

Test outcomes must be `passed`, `failed`, `blocked`, or `not_run`. Include every
planned case, not just successful or executed cases. The export evaluates these
supplied outcomes; it does not execute functional tests or run clustering.

The calculation uses the positive hotspot class:

- Precision = TP / (TP + FP)
- Recall = TP / (TP + FN)
- F1 = 2TP / (2TP + FP + FN)
- Algorithmic performance score = F1
- Functional score = passed cases / all supplied cases
- Overall effectiveness (%) = 100 × (0.90 × classification + 0.10 × functional)

Precision and Recall are reported as supporting measures. F1 alone supplies the 90% algorithmic component.
A zero denominator produces 0 and this convention is recorded in the export.
Empty evidence or mismatched units produces an error, not a score.

The Excel workbook includes a formatted summary, provenance, scope, confusion
matrix, metrics, test counts, weights, contributions, formulas, matched labels,
and individual test outcomes on separate evidence sheets.
The incident filters do not apply to this separate evidence upload. Results
are downloaded directly and are not saved to the algorithm evaluations table.
Authenticated API clients can POST the CSV text as `predictions_csv`,
`reference_csv`, and `functional_tests_csv`, together with `reference_source`,
`validated_by`, and `scope`, to `/api/reports/evaluation`.

## Temporal split evaluation (real-data alternative)

The manual export above needs a `reference_csv` from a source independent of
the algorithm. The PNP data-sharing request behind this study covers
incident-level fields only (crime type, date, municipality, barangay,
location, coordinates) — it does not include a separately certified hotspot
list, so there is no such independent file to upload for a genuinely
real-data evaluation.

**Reports → Temporal split evaluation** solves this using only the incident
data already covered by that request. Pick a cutoff date, dataset (synthetic
or the uploaded PNP data), and DBSCAN/grid parameters. The tool then:

1. Runs DBSCAN on incidents strictly before the cutoff date (the training
   window) to get predicted hotspot grid cells.
2. Checks whether an incident actually occurred in each grid cell on or after
   the cutoff date (the test window, held out from clustering) as the
   reference label.
3. Computes the same confusion matrix, precision, recall, and F1 as above.

Because the algorithm never sees the test-window incidents when producing its
predictions, this is a genuine external validation — not circular — built
entirely from data already licensed from PNP. It mirrors the predictive
accuracy checks used in hotspot-policing literature, and it needs no separate
PNP hotspot certification. It works over synthetic data for demonstration and
over uploaded PNP data for the real result, via `POST
/api/reports/evaluation/temporal-split` (`cutoff_date`, `source`, optional
`municipality`/`crime_type`, `eps_km`, `min_samples`, `cell_km`). The
generated `predictions_csv`/`reference_csv` use the same format as the manual
export and can be paired with a real `functional_tests_csv` there for the
full 90/10 workbook.
