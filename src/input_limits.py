"""Bound the work accepted by the public demonstration app."""

from io import BytesIO

import pandas as pd


MAX_UPLOAD_MB = 5
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024
MAX_DATA_ROWS = 20_000
MAX_DATA_COLUMNS = 32
MAX_REFERENCE_BATCHES = 50
MAX_TIME_POINTS_PER_BATCH = 1_000


class UploadLimitError(ValueError):
    """An uploaded dataset exceeds the public demo's resource limits."""


def resource_limit_errors(data: pd.DataFrame) -> list[str]:
    """Check cheap size limits before validation and model training."""
    errors = []
    if len(data) > MAX_DATA_ROWS:
        errors.append(f"The public demo accepts at most {MAX_DATA_ROWS:,} rows.")
    if len(data.columns) > MAX_DATA_COLUMNS:
        errors.append(
            f"The public demo accepts at most {MAX_DATA_COLUMNS} columns."
        )
    if errors:
        return errors

    if "batch_id" in data.columns:
        if (data.groupby("batch_id").size() > MAX_TIME_POINTS_PER_BATCH).any():
            errors.append(
                "The public demo accepts at most "
                f"{MAX_TIME_POINTS_PER_BATCH:,} observations per batch."
            )
        if "batch_role" in data.columns:
            reference_count = data.loc[
                data["batch_role"] == "reference", "batch_id"
            ].nunique()
            if reference_count > MAX_REFERENCE_BATCHES:
                errors.append(
                    "The public demo accepts at most "
                    f"{MAX_REFERENCE_BATCHES} reference batches."
                )
    return errors


def read_uploaded_csv(uploaded_file) -> pd.DataFrame:
    """Read a bounded amount of data; never use the uploaded filename."""
    uploaded_file.seek(0)
    raw = uploaded_file.read(MAX_UPLOAD_BYTES + 1)
    if len(raw) > MAX_UPLOAD_BYTES:
        raise UploadLimitError(
            f"The public demo accepts CSV files up to {MAX_UPLOAD_MB} MB."
        )

    # The extra row detects an oversized file instead of silently truncating it.
    data = pd.read_csv(BytesIO(raw), nrows=MAX_DATA_ROWS + 1)
    errors = resource_limit_errors(data)
    if errors:
        raise UploadLimitError(" ".join(errors))
    return data
