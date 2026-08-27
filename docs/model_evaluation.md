# Model Evaluation

## 1. Purpose

This document records how the anomaly-detection methods were evaluated against the known synthetic ground truth.

The evaluation is performed at the time-point level. A time point is considered anomalous if it belongs to either injected anomaly interval.

## 2. Evaluation dataset

The synthetic demonstration dataset contains:

* twenty reference batches;
* one assessment batch;
* 241 hourly observations per batch;
* five monitored process variables;
* two deliberately injected anomaly events.

The known anomaly intervals are:

| Event                          | Time interval | Affected variables                      |
| ------------------------------ | ------------: | --------------------------------------- |
| Feed-rate reduction            |     120–144 h | `feed_rate_ml_h`                        |
| Oxygen and agitation deviation |     170–190 h | `dissolved_oxygen_pct`, `agitation_rpm` |

Together, these events contain 46 unique anomalous time points.

The dataset is synthetic and educational. It does not represent a real manufacturing process or operating recipe.

## 3. Evaluated methods

### Robust Z-score detector

The interpretable detector compares each assessment value with the reference batches at the same elapsed time.

It uses:

* the reference median as the expected value;
* the median absolute deviation as a robust measure of variability;
* an absolute robust Z-score threshold of `5.0`.

This method also identifies which process variable caused each flag.

### Isolation Forest

Isolation Forest is trained only on normalized observations from the reference batches.

The implementation uses:

* five normalized process variables;
* 300 isolation trees;
* a fixed random seed of `42`;
* an anomaly threshold based on the 99.5th percentile of the reference anomaly scores.

The threshold is derived from reference data, not from the assessment-batch ground truth.

## 4. Results

| Model            | True positives | False positives | False negatives | True negatives | Precision | Recall | F1 score |
| ---------------- | -------------: | --------------: | --------------: | -------------: | --------: | -----: | -------: |
| Robust Z-score   |             46 |               0 |               0 |            195 |    100.0% | 100.0% |   100.0% |
| Isolation Forest |             42 |              10 |               4 |            185 |     80.8% |  91.3% |    85.7% |

## 5. Isolation Forest error analysis

Isolation Forest missed the following anomalous hours: `121, 133, 134, 135`.

It produced false-positive flags at: `30, 35, 38, 90, 104, 145, 219, 221, 231, 236`.

The model detected the complete oxygen and agitation event from 170 to 190 hours.

## 6. Interpretation

The Robust Z-score detector performed perfectly on this synthetic scenario. This does not prove that it will be universally superior on real data.

The injected anomalies were deliberately created as clear deviations from the reference trajectories, which directly matches the assumptions of the interpretable detector.

Isolation Forest provides an independent multivariate view. It detects unusual combinations of variables but does not directly explain which variable caused a flag.

The MVP therefore uses:

* the Robust Z-score detector for primary detection and explanation;
* Isolation Forest for independent multivariate corroboration;
* explicit review when the two methods disagree.

## 7. Threshold policy

The Isolation Forest threshold was not adjusted after examining the assessment-batch ground truth.

Changing the threshold to improve performance on the same assessment batch would create evaluation leakage and an overly optimistic result.

Future threshold development would require separate validation and test datasets.

## 8. Limitations

This evaluation:

* uses only synthetic data;
* contains only two injected anomaly types;
* uses one assessment batch;
* does not evaluate robustness across different processes or equipment scales;
* does not establish acceptable operating ranges;
* does not establish GMP suitability;
* does not support batch-release or patient-safety decisions.

Performance on this dataset must not be interpreted as expected performance on real manufacturing data.

## 9. Reproducibility

The evaluation can be reproduced inside the project environment with `python -m src.model_evaluation`.

The automated test suite can be executed with `python -m pytest -q`.

At the time of this evaluation, all ten automated tests pass.
