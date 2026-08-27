# Data Contract

## 1. Purpose

This document defines the structure and basic quality rules for data uploaded to the Bioprocess Intelligence Copilot.

A clear data contract prevents the application from analysing incomplete, inconsistent, or incorrectly formatted data.

Each row represents one measurement time point from one batch.

## 2. Required columns

| Column | Meaning | Data type | Unit or allowed value |
|---|---|---|---|
| `batch_id` | Unique name of the batch | Text | Example: `REF_001` |
| `batch_role` | How the batch is used | Text | `reference` or `assessment` |
| `elapsed_time_h` | Time since the start of the batch | Number | Hours |
| `ph` | Acidity or alkalinity | Number | pH units |
| `dissolved_oxygen_pct` | Dissolved oxygen level | Number | Percent |
| `temperature_c` | Process temperature | Number | Degrees Celsius |
| `agitation_rpm` | Impeller rotation speed | Number | Revolutions per minute |
| `feed_rate_ml_h` | Nutrient feed rate | Number | Millilitres per hour |

Column names must match this table exactly.

## 3. Batch roles

A **reference batch** contributes to the expected process behaviour.

An **assessment batch** is the batch being investigated.

Each uploaded dataset must contain:

- exactly one assessment batch;
- at least ten reference batches.

The minimum of ten reference batches is an MVP assumption, not a scientifically validated universal requirement.

The synthetic demonstration dataset will contain twenty reference batches and one assessment batch.

## 4. File-format rules

The uploaded file must:

- use the CSV format;
- use commas to separate values;
- use a period as the decimal separator;
- contain all required columns;
- contain no empty values in required columns;
- use the same units for every batch;
- contain only finite numeric values in measurement columns.

The application will not automatically guess units or convert mixed units.

## 5. Time-series rules

Within each batch:

- elapsed time must start at zero or later;
- each time point must appear only once;
- time must move forward;
- all batches must contain the same measurement times.

Using the same time grid is an MVP design choice. It makes batch comparison transparent and avoids hidden interpolation during the first version.

The synthetic demonstration data will use measurements from 0 to 240 hours at one-hour intervals.

## 6. Basic value rules

The following values are invalid:

- pH below 0 or above 14;
- negative dissolved oxygen;
- negative agitation rate;
- negative feed rate;
- negative elapsed time;
- text inside a numeric measurement column;
- missing or infinite numeric values.

Unusual values are not automatically invalid. A value may be technically possible but still unusual compared with the reference batches.

## 7. Duplicate observations

The combination of:

- `batch_id`;
- `elapsed_time_h`;

must be unique.

If the same batch contains two observations at the same elapsed time, the application must stop and report the duplicate.

## 8. Batch comparability

The application can compare numbers, but it cannot prove that batches are scientifically comparable.

The user remains responsible for confirming that the batches represent the same:

- process type;
- general operating strategy;
- equipment scale or justified comparable scale;
- sampling approach;
- measurement units.

If these conditions are not met, the comparison may be misleading.

## 9. Validation behaviour

The application will separate problems into two groups.

### Errors

Errors stop the analysis. Examples include:

- missing required columns;
- invalid batch roles;
- more than one assessment batch;
- too few reference batches;
- duplicated observations;
- missing required values;
- inconsistent measurement times.

### Warnings

Warnings allow the analysis to continue but require user attention. Examples include:

- values far outside the reference-batch distribution;
- unusually short process duration;
- large differences between batches;
- values outside the expected region of the synthetic demonstration.

A warning does not prove that the data are wrong.

## 10. Example

```csv
batch_id,batch_role,elapsed_time_h,ph,dissolved_oxygen_pct,temperature_c,agitation_rpm,feed_rate_ml_h
REF_001,reference,0,7.10,40.0,36.8,100,0
REF_001,reference,1,7.08,38.5,36.8,105,0
ASSESS_001,assessment,0,7.11,40.5,36.8,100,0
ASSESS_001,assessment,1,7.07,37.9,36.8,105,0
