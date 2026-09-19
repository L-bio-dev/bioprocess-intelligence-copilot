# Public demo: limits and security checks

The public app accepts CSV files up to 5 MB, with at most:

- 20,000 rows in total;
- 32 columns;
- 50 reference batches;
- 1,000 observations per batch.

All limits apply together. The existing rules still require at least ten
reference batches, exactly one assessment batch, and the same measurement
times across batches. Extra columns count towards the column limit.

These limits are initial engineering choices to keep the demo manageable.
They are not scientific requirements or measured guarantees about server
capacity. Multiple simultaneous users can still exhaust available resources.

The CSV reader stops after one row beyond the row limit and rejects oversized
datasets before running the detectors. It never silently analyses a truncated
dataset. Uploaded filenames are not used as server file paths.

Analysis failures show a generic message instead of the exception details.

## Event timing

Event summaries preserve the original measurement times, including fractional
hours. An event groups consecutive observed time points flagged by the robust
detector. A normal point, including an ML-only flag, separates events.

Consecutive means adjacent observations on the shared measurement grid, not
necessarily one hour apart. With irregular or sparse sampling, an event window
can span a long gap. No behaviour is inferred between measurements, and its
start and end do not establish the true duration of a deviation.

ML corroboration is the percentage of flagged observations in the event also
flagged by Isolation Forest. It is not a time-weighted percentage.

The synthetic benchmark and its evaluation remain based on integer hourly data.

## Scope of the review

The review covered supplied source code and configuration, a pip-audit check
of the pinned requirements, and the GitHub secret-scanning results shown by
the project owner. Neither scanner reported findings at the time of review.
Account two-factor authentication was also enabled.

This was not a penetration test, a full infrastructure audit, or evidence that
all possible vulnerabilities are absent. Dependency and secret checks should
be repeated as the project changes.
