"""Describe detected events using calculated evidence and fixed wording."""

import pandas as pd


VARIABLE_NAMES = {
    "ph": "pH",
    "dissolved_oxygen_pct": "Dissolved oxygen (%)",
    "temperature_c": "Temperature (°C)",
    "agitation_rpm": "Agitation (rpm)",
    "feed_rate_ml_h": "Feed rate (mL/h)",
}


def explain_event(event: pd.Series, scores: pd.DataFrame) -> dict:
    """Summarise flagged measurements, never infer a process cause."""
    start = float(event["start_time_h"])
    end = float(event["end_time_h"])
    count = int(event["flagged_time_points"])
    corroborated = int(event["ml_corroborated_time_points"])

    if count <= 0 or not 0 <= corroborated <= count:
        raise ValueError("Inconsistent event observation counts.")

    if start == end:
        time_description = f"At {start:g} h"
    else:
        time_description = f"From {start:g} to {end:g} h"

    noun = "observation" if count == 1 else "observations"
    overview = (
        f"{time_description}, the robust Z-score detector flagged "
        f"{count} {noun} in the batch being reviewed. "
        "At each flagged time point, at least one process variable "
        "crossed the configured anomaly threshold."
    )

    flagged = scores.loc[
        scores["is_anomaly"]
        & scores["elapsed_time_h"].between(start, end)
    ]
    notes = []

    for variable, variable_scores in flagged.groupby("variable", sort=True):
        z_scores = variable_scores["robust_z_score"]
        if (z_scores > 0).all():
            direction = "above the reference median"
        elif (z_scores < 0).all():
            direction = "below the reference median"
        else:
            direction = "on both sides of the reference median"

        # Select by magnitude: a large negative deviation also matters.
        peak = variable_scores.iloc[z_scores.abs().to_numpy().argmax()]
        variable_count = len(variable_scores)
        variable_noun = "observation" if variable_count == 1 else "observations"
        label = VARIABLE_NAMES.get(variable, variable.replace("_", " "))

        notes.append(
            f"{label}: {variable_count} flagged {variable_noun}, {direction}. "
            "The largest absolute robust Z-score was "
            f"{abs(float(peak['robust_z_score'])):.2f} "
            f"at {float(peak['elapsed_time_h']):g} h "
            f"(measured value: {float(peak['assessment_value']):.4g}; "
            f"reference median: {float(peak['reference_median']):.4g})."
        )

    if not notes:
        raise ValueError("No flagged measurements found for this event.")

    time_noun = "time point" if count == 1 else "time points"
    agreement = (
        "Isolation Forest also flagged "
        f"{corroborated} of the {count} flagged {time_noun} "
        f"({100 * corroborated / count:.1f}%). "
        "This is agreement between detectors, not a probability "
        "that the batch has a problem or confirmation of a cause."
    )

    return {
        "overview": overview,
        "variable_notes": notes,
        "agreement": agreement,
        "limitation": (
            "These results identify deviations from the reference data. "
            "They do not establish a root cause or batch acceptability. "
            "The event window covers observed time points; behaviour "
            "between measurements is unknown."
        ),
    }
