# Synthetic scenario evaluation

This benchmark asks how the existing detectors behave beyond the original
demonstration batch. It is an exploratory synthetic benchmark, not evidence of
performance on manufacturing data or a validated operating procedure.

## Run

```bash
python -m src.scenario_evaluation
```

The default evaluates six scenarios for each of five fixed seeds
(`1001, 1002, 1003, 1004, 1005`): 30 datasets, each with 20 reference batches
and one assessment batch, and 60 detector evaluations. Each batch contains
241 measurements, at integer hours from 0 to 240 inclusive.

For a quick execution check, use `python -m src.scenario_evaluation --seeds 1001`.
This uses the same output directory and overwrites previous benchmark results;
run the default command afterwards for the five-seed report. Alternatively,
use `--output-dir` to keep separate runs.

## Scenarios fixed before examining results

| Scenario | Change to the assessment batch | Labelled anomalous points |
| --- | --- | ---: |
| `no_injected_anomalies` | No injected change | 0 |
| `clear_deviations` | Feed reduced by 35% at 120–144 h; oxygen reduced by 12 percentage points and agitation increased by 45 rpm at 170–190 h | 46 |
| `mild_deviations` | Feed reduced by 10% at 120–144 h; oxygen reduced by 3 percentage points and agitation increased by 10 rpm at 170–190 h | 46 |
| `gradual_feed_drift` | Feed reduction increases linearly from 35/61% at 120 h to 35% at 180 h; original trajectory resumes at 181 h | 61 |
| `higher_variability_no_anomalies` | Double deviations from the base trajectory in both reference and assessment batches; no injected event | 0 |
| `higher_variability_clear_deviations` | Same increased variability, with the clear deviations above | 46 |

All scenarios for a given seed start from identical random draws. This pairing
helps compare the effect of each controlled change. Different seeds generate
new references and a new assessment batch. The high-variability transformation
scales both batch offsets and measurement noise around the generator's base
profiles; it does not introduce new process physics. Physical bounds used by
the demo generator are retained where applicable, so clipping can prevent an
exact doubling near a bound.

Changes are applied to the generator's already-rounded output, without a second
rounding step. The clear-deviation scenario uses the original event magnitudes
but is not a byte-for-byte reproduction of the original demonstration dataset.

## Detector policy

The existing production functions are reused. Robust Z-score keeps its current
threshold of 5. Isolation Forest keeps 300 trees, model seed 42, and a threshold
computed from the 99.5th percentile of each run's reference scores. Its numeric
threshold may change with the references; its calibration rule stays fixed.
Neither detector receives the injected-event labels. Labels are used for
evaluation only; neither thresholds nor scenario definitions are optimized
against these results.

## Outputs and interpretation

Results are written separately under `data/processed/scenario_evaluation/`:

- `runs.csv`: confusion counts and metrics for each seed, scenario and model.
- `summary.csv`: pooled counts and metrics for each scenario and model, plus
  minimum/maximum recall and false-alarm counts across assessment batches.
- `manifest.json`: seeds, scenarios, threshold settings and package versions.

Precision, recall, F1 and false-positive rate are ratios from 0 to 1. For example,
`0.20` means 20%. The false-positive rate is FP / (FP + TN): the proportion of
non-injected time points incorrectly flagged according to the synthetic labels.
`batches_with_false_alarms_fraction` is the fraction of assessment batches with
at least one such flag, including normal periods in event-containing batches.

Blank CSV cells (NaN in the terminal) mean undefined, not zero. Precision is
undefined if nothing was flagged. Recall and anomaly F1 are deliberately not
reported for scenarios with no injected anomalies; assess their false alarms.
Summary rates are calculated from pooled counts, not averages of per-run ratios.
The reported ranges show observed variation across five runs, not confidence
intervals. One flagged time point counts once even if multiple variables flag.

## Limits

"No injected anomaly" is a synthetic ground-truth convention. Random variation
can still produce unusual values; a flag is counted as a false positive in this
benchmark without establishing that the method is faulty in a real process.
Every nonzero injected drift point is labelled anomalous, including the earliest
very small changes. Imperfect recall is therefore expected for subtle drift.

Five seeds provide an initial sensitivity check, not a large independent test
set. Scenarios share the same generator and paired reference sets; time points
within a batch are correlated. The benchmark measures time-point detection,
not root-cause accuracy, event-duration accuracy or detection latency. It does
not validate uploaded customer data, operating limits, GMP use or batch release.

If these results motivate threshold tuning, treat these seeds as development
data and reserve new batches/seeds for a separate final evaluation. The original
demo CSV files, its benchmark table and the Streamlit interface are unchanged.

## Recorded five-seed results

The default evaluation completed in the project Codespace with seeds
1001–1005. The automated suite passed 51 tests and 15 subtests. The table below
transcribes the terminal summary; ratios are rounded to three decimal places.
Full-precision values and individual runs are in the generated CSV files. The
package versions for this execution are recorded in its `manifest.json`.

| Scenario | Model | Precision | Recall | F1 | False-positive rate | Mean false-positive points per batch |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| No injected anomalies | Robust Z-score | 0.000 | N/A | N/A | 0.007 | 1.6 |
| No injected anomalies | Isolation Forest | 0.000 | N/A | N/A | 0.126 | 30.4 |
| Clear deviations | Robust Z-score | 0.975 | 1.000 | 0.987 | 0.006 | 1.2 |
| Clear deviations | Isolation Forest | 0.538 | 0.613 | 0.573 | 0.124 | 24.2 |
| Mild deviations | Robust Z-score | 0.900 | 0.235 | 0.372 | 0.006 | 1.2 |
| Mild deviations | Isolation Forest | 0.328 | 0.257 | 0.288 | 0.124 | 24.2 |
| Gradual feed drift | Robust Z-score | 0.967 | 0.679 | 0.798 | 0.008 | 1.4 |
| Gradual feed drift | Isolation Forest | 0.427 | 0.259 | 0.322 | 0.118 | 21.2 |
| Higher variability, no anomalies | Robust Z-score | 0.000 | N/A | N/A | 0.007 | 1.6 |
| Higher variability, no anomalies | Isolation Forest | 0.000 | N/A | N/A | 0.126 | 30.4 |
| Higher variability, clear deviations | Robust Z-score | 0.967 | 0.774 | 0.860 | 0.006 | 1.2 |
| Higher variability, clear deviations | Isolation Forest | 0.498 | 0.522 | 0.510 | 0.124 | 24.2 |

### What these results support

- Robust Z-score detected all injected time points in the clear-deviation
  scenario, but also produced false positives: its precision was about 97.5%.
  It was not perfect across these new datasets.
- Sensitivity fell for mild changes: recall was about 23.5% for Robust Z-score
  and 25.7% for Isolation Forest. Neither configuration reliably captured these
  smaller injected deviations.
- For gradual feed drift, recall was about 67.9% and 25.9%, respectively. The
  labels include the earliest, smallest changes; recall alone does not establish
  the time to first detection.
- With higher variability and clear deviations, recall fell to about 77.4% and
  52.2%, respectively. Reference variability materially affects detection.
- In the scenario without injected anomalies, Isolation Forest flagged an
  average of 30.4 of 241 time points per batch, versus 1.6 for Robust Z-score.
  These are point counts, not counts of independent events or affected batches.
  The secondary detector therefore introduces a substantial review burden in
  this benchmark. It should not be presented as a reliability guarantee.

The Isolation Forest reference-score quantile is a calibration rule applied to
training references, not a guarantee of a 0.5% false-positive rate on new batches.
The original demo results remain valid for that particular dataset; this wider
benchmark limits the conclusions that can be drawn from them. These five seeds
and synthetic scenarios do not establish superiority on real manufacturing data.

### Development decision

Keep both detector configurations unchanged while recording these results.
The next priorities are to investigate false alarms on separate normal batches
and to measure sensitivity to smaller deviations. If development uses these
results to select settings, use separate batches/seeds for final evaluation.
Any proposed change must report both missed anomalies and false alarms.

A future in-app benchmark summary should distinguish this evaluation from the
original demonstration and from the analysis of a user's uploaded dataset.
