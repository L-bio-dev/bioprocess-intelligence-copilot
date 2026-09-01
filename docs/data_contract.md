# Data Contract

## 1. Purpose

This document describes the CSV structure accepted by Bioprocess Intelligence Copilot and the checks performed before the analysis begins.

Each row represents one measurement time point from one batch.

Passing these checks means that the dataset has the required technical structure. It does not prove that the batches are scientifically suitable for comparison.

## 2. Required columns

| Column                 | Meaning                           | Type or allowed value             |
| ---------------------- | --------------------------------- | --------------------------------- |
| `batch_id`             | Identifier of the batch           | Text, for example `REF_001`       |
| `batch_role`           | Role of the batch in the analysis | `reference` or `assessment`       |
| `elapsed_time_h`       | Time since the start of the batch | Number, in hours                  |
| `ph`                   | pH measurement                    | Number                            |
| `dissolved_oxygen_pct` | Dissolved oxygen                  | Number, in percent                |
| `temperature_c`        | Process temperature               | Number, in degrees Celsius        |
| `agitation_rpm`        | Impeller rotation speed           | Number, in revolutions per minute |
| `feed_rate_ml_h`       | Nutrient feed rate                | Number, in millilitres per hour   |

Column names must match this table exactly.

Additional columns do not stop the analysis, but the application displays a warning and ignores them.

## 3. Batch structure

Each dataset must contain:

* exactly one assessment batch;
* at least ten reference batches;
* one consistent role for each batch identifier.

The assessment batch is the run being checked. The reference batches are the runs used for comparison.

These roles do not automatically mean that the assessment batch is bad or that every reference batch is good.

The minimum of ten reference batches is a design choice for this project. It is not a scientifically validated minimum for every bioprocess.

The built-in demonstration contains twenty reference batches and one assessment batch.

## 4. CSV format

The application expects:

* a CSV file;
* commas as column separators;
* periods as decimal separators;
* all required columns;
* no empty values in required columns;
* numeric values in all measurement columns;
* no infinite numeric values.

Uploaded files are limited to 25 MB.

The application does not identify units from the values and does not convert between units. The user must make sure that every batch uses the same units and measurement conventions.

## 5. Time-point rules

Elapsed time must be numeric and cannot be negative.

The combination of `batch_id` and `elapsed_time_h` must be unique. If the same batch contains more than one row for the same time point, the analysis stops.

All batches must contain the same measurement times. This allows the application to compare values at the same elapsed time without interpolation.

Rows within each batch should be ordered by elapsed time. An incorrect row order produces a warning, but it does not stop the analysis.

The built-in demonstration contains measurements from hour 0 to hour 240 at one-hour intervals. An uploaded dataset is not required to use this exact interval, but every batch in that dataset must use the same time grid.

## 6. Value checks

The following conditions stop the analysis:

* empty batch identifiers;
* missing required values;
* text or other non-numeric content in numeric columns;
* infinite numeric values;
* pH below 0 or above 14;
* negative elapsed time;
* negative dissolved oxygen;
* negative agitation;
* negative feed rate;
* unsupported batch roles;
* a batch identifier assigned to more than one role;
* fewer than ten reference batches;
* anything other than exactly one assessment batch;
* duplicated batch-time observations;
* different measurement times across batches.

Temperature must be numeric and finite, but the current validator does not apply a minimum or maximum temperature limit.

The validator also does not apply an upper limit to dissolved oxygen, agitation or feed rate.

A value can therefore pass the input checks and still be scientifically implausible or unusual. Input validation and anomaly detection are separate steps.

## 7. Warnings

Warnings allow the analysis to continue.

The current validator produces warnings in two situations:

* the dataset contains additional columns that are not used by the analysis;
* the rows of a batch are not ordered by elapsed time.

Unusual measurements are handled later by the anomaly-detection methods. They are not input-validation warnings.

## 8. Scientific comparability

The application can compare numerical measurements, but it cannot prove that the selected batches are scientifically comparable.

The user is responsible for checking that the batches have suitable similarities, including:

* process type;
* operating strategy;
* equipment scale, or a justified comparable scale;
* sampling approach;
* measurement methods;
* measurement units.

If these conditions are not satisfied, the comparison may be misleading even when the file passes every validation check.

The application does not determine whether any of the five measurements is a critical process parameter.

## 9. Short format example

```csv
batch_id,batch_role,elapsed_time_h,ph,dissolved_oxygen_pct,temperature_c,agitation_rpm,feed_rate_ml_h
REF_001,reference,0,7.10,40.0,36.8,100,0
REF_001,reference,1,7.08,38.5,36.8,105,0
ASSESS_001,assessment,0,7.11,40.5,36.8,100,0
ASSESS_001,assessment,1,7.07,37.9,36.8,105,0
```

This short example only shows the required format. It does not contain the minimum number of reference batches needed to pass validation.
