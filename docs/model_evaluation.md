# Model Evaluation

## 1. Purpose

This document explains how the two anomaly-detection methods were evaluated using the known changes in the synthetic demonstration dataset.

The evaluation is performed at the time-point level. An hour is treated as anomalous when it belongs to one of the two injected event intervals.

If more than one variable is flagged during the same hour, that hour is counted only once.

## 2. Evaluation dataset

The synthetic dataset contains:

* twenty reference batches;
* one assessment batch;
* 241 hourly observations per batch, from hour 0 to hour 240;
* five process variables;
* two deliberately injected events.

| Event                          | Time interval | Modified variables                      |
| ------------------------------ | ------------: | --------------------------------------- |
| Feed-rate reduction            |     120–144 h | `feed_rate_ml_h`                        |
| Oxygen and agitation deviation |     170–190 h | `dissolved_oxygen_pct`, `agitation_rpm` |

The first interval contains 25 time points and the second contains 21. Together, they contain 46 unique anomalous time points.

The dataset is simulated and does not represent a real manufacturing process or operating recipe.

## 3. Ground truth

The known event intervals are stored separately from the process measurements.

The detectors receive the process dataset but do not receive the ground-truth intervals. Ground truth is used afterward to compare the expected anomalous hours with the hours flagged by each detector.

This separation means that ground truth is not used directly when fitting Isolation Forest, calculating reference statistics or scoring the assessment batch.

## 4. Robust Z-score detector

The Robust Z-score detector compares every assessment value with the reference values for the same variable at the same elapsed time.

For each variable and time point, it calculates:

* the reference median;
* the Median Absolute Deviation, or MAD;
* a robust reference scale equal to `1.4826 × MAD`.

The score is calculated as:

```text
(assessment value - reference median) / reference scale
```

A value is flagged when the absolute score is greater than or equal to `5.0`.

If the robust scale is almost zero, the implementation uses the sample standard deviation. If that is also almost zero, it uses `1e-9` to avoid division by zero.

The detector evaluates the five variables separately. It therefore shows which variable triggered a statistical flag. It does not establish the biological or process cause of that deviation.

## 5. Isolation Forest

Isolation Forest provides a separate multivariate check.

Before the model is fitted, every variable is normalized using the reference median and reference scale calculated for the same elapsed time.

The model is fitted only on normalized observations from the reference batches. The assessment batch is scored afterward.

The implementation uses:

* five normalized process variables;
* 300 isolation trees;
* a fixed random seed of `42`;
* a custom threshold based on the 99.5th percentile of the reference anomaly scores.

A time point is flagged when its assessment anomaly score is greater than or equal to this reference threshold.

The threshold is calculated from pooled reference anomaly scores. Assessment values and ground-truth labels are not used in the threshold calculation.

Each assessment hour is evaluated as one multivariate observation. The model does not receive the preceding hours as a sequence and does not directly recognise trends such as a measurement decreasing for several consecutive hours.

Isolation Forest also does not identify which individual variable produced its multivariate flag.

## 6. Evaluation metrics

The evaluation compares expected anomalous hours with flagged hours.

* **True positive:** an injected anomalous hour that was flagged.
* **False positive:** an hour outside the injected events that was flagged.
* **False negative:** an injected anomalous hour that was not flagged.
* **True negative:** an hour outside the injected events that was not flagged.
* **Precision:** the proportion of flagged hours that belonged to an injected event.
* **Recall:** the proportion of injected anomalous hours that were detected.
* **F1 score:** a combined measure of precision and recall.

## 7. Results

| Detector         | True positives | False positives | False negatives | True negatives | Precision | Recall | F1 score |
| ---------------- | -------------: | --------------: | --------------: | -------------: | --------: | -----: | -------: |
| Robust Z-score   |             46 |               0 |               0 |            195 |    100.0% | 100.0% |   100.0% |
| Isolation Forest |             42 |              10 |               4 |            185 |     80.8% |  91.3% |    85.7% |

The totals for each detector equal the 241 assessment time points.

## 8. Isolation Forest error analysis

Isolation Forest missed these anomalous hours:

```text
121, 133, 134, 135
```

It produced additional flags at:

```text
30, 35, 38, 90, 104, 145, 219, 221, 231, 236
```

Isolation Forest flagged all 21 time points in the second injected event, from hour 170 to hour 190.

This means that the model detected every hour in that event. It does not mean that it separately identified dissolved oxygen and agitation as the responsible variables.

## 9. Interpretation

The Robust Z-score detector produced perfect time-point results in this synthetic demonstration.

The injected events were designed as clear deviations from the reference trajectories. This structure closely matches what the Robust Z-score detector is designed to find. Its perfect result must therefore not be treated as evidence of perfect performance on real data.

Isolation Forest detected 42 of the 46 injected anomalous hours and generated 10 additional flags. It examines the five variables together, but its flags are less directly interpretable.

The application uses:

* Robust Z-score for primary variable-level detection;
* Isolation Forest as a separate multivariate check;
* a review category when Isolation Forest flags a point that the Robust Z-score detector does not.

Disagreement between the detectors does not, by itself, show which detector is correct.

## 10. Threshold choices and evaluation leakage

During execution, the Robust Z-score threshold is fixed at `5.0`. The Isolation Forest threshold is calculated only from reference anomaly scores.

The ground-truth intervals are not passed into either detector.

However, reporting performance on the same synthetic scenario used during development does not provide an independent estimate of future performance. Repeatedly changing detector settings after examining these results could produce an overly optimistic evaluation.

A stronger future evaluation would use separate datasets for development, threshold selection and final testing.

## 11. Limitations

This evaluation:

* uses only simulated data;
* contains only two injected event types;
* uses one assessment batch;
* evaluates time-point detection rather than root-cause identification;
* does not test different processes, products or equipment scales;
* does not establish normal operating ranges or specification limits;
* does not establish performance on uploaded datasets;
* does not establish GMP suitability.

The results must not be used to support batch release, process control, patient-safety decisions or expected performance on real manufacturing data.

## 12. Reproducing the evaluation

Run the evaluation inside the project environment with:

```bash
python -m src.model_evaluation
```

Run the automated tests with:

```bash
python -m pytest -q
```

The number of tests is not recorded here because it can change as the project develops. The terminal output provides the current result.
