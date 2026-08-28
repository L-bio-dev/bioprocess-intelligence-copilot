"""Streamlit interface for the Bioprocess Intelligence Copilot."""

from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.anomaly_detection import score_assessment_batch
from src.data_validation import validate_dataset
from src.event_summary import (
    create_hourly_consensus,
    summarize_process_events,
)
from src.isolation_forest_detection import (
    score_with_isolation_forest,
)


PROJECT_ROOT = Path(__file__).resolve().parent

DEMO_DATA_PATH = (
    PROJECT_ROOT
    / "data"
    / "synthetic"
    / "bioprocess_batches.csv"
)


st.set_page_config(
    page_title="Bioprocess Intelligence Copilot",
    page_icon="🧬",
    layout="wide",
)
st.image(
    PROJECT_ROOT / "assets" / "bioprocess_logo_cropped.png",
width=600,
)


st.caption(
    "An educational decision-support prototype for comparing "
    "an assessment batch with reference-batch trajectories."
)

st.warning(
    "Demonstration only. This application is not validated for GMP, "
    "batch release, process control, or patient-safety decisions."
)


st.sidebar.header("Data source")

data_source = st.sidebar.radio(
    "Choose the dataset",
    options=[
        "Synthetic demonstration",
        "Upload CSV",
    ],
)

uploaded_file = None

if data_source == "Upload CSV":
    uploaded_file = st.sidebar.file_uploader(
        "Upload a CSV following the documented data contract",
        type=["csv"],
        max_upload_size=25,
    )

    st.sidebar.caption(
        "Do not upload confidential, personal, regulated, "
        "or proprietary manufacturing data."
    )


if data_source == "Synthetic demonstration":
    data = pd.read_csv(DEMO_DATA_PATH)
    source_label = "Built-in synthetic demonstration dataset"

elif uploaded_file is None:
    st.info(
        "Upload a CSV file from the sidebar to begin validation."
    )
    st.stop()

else:
    try:
        data = pd.read_csv(uploaded_file)
    except (
        pd.errors.ParserError,
        UnicodeDecodeError,
        ValueError,
    ):
        st.error(
            "The uploaded file could not be read as a valid CSV."
        )
        st.stop()

    source_label = f"Uploaded file: {uploaded_file.name}"


st.subheader("Input validation")

validation = validate_dataset(data)

if not validation.is_valid:
    st.error("The dataset cannot be analysed.")

    for error in validation.errors:
        st.error(error)

    st.stop()


st.success("The dataset passed all blocking validation checks.")

for warning in validation.warnings:
    st.warning(warning)


reference_count = data.loc[
    data["batch_role"] == "reference",
    "batch_id",
].nunique()

assessment_batch_id = data.loc[
    data["batch_role"] == "assessment",
    "batch_id",
].unique()[0]

assessment_time_points = len(
    data[data["batch_role"] == "assessment"]
)


st.subheader("Dataset overview")

metric_columns = st.columns(4)

metric_columns[0].metric(
    "Reference batches",
    reference_count,
)

metric_columns[1].metric(
    "Assessment batch",
    assessment_batch_id,
)

metric_columns[2].metric(
    "Assessment time points",
    assessment_time_points,
)

metric_columns[3].metric(
    "Total rows",
    len(data),
)


st.caption(source_label)

st.subheader("Data preview")
if validation.is_valid:
    try:
        with st.spinner("Running anomaly detection..."):
            interpretable_scores = score_assessment_batch(data)

            ml_scores = score_with_isolation_forest(data)

            detector_consensus = create_hourly_consensus(
                interpretable_scores,
                ml_scores,
            )

            process_events = summarize_process_events(
                detector_consensus
            )

    except (ValueError, KeyError, TypeError) as error:
        st.error(
            "The dataset passed structural validation, but the "
            "analysis could not be completed."
        )
        st.caption(str(error))
        st.stop()

    model_evaluation = pd.read_csv(
        PROJECT_ROOT
        / "data"
        / "processed"
        / "model_evaluation.csv"
    )

    st.divider()
    st.subheader("Process intelligence")

    st.caption(
        "The interpretable detector identifies variable-level deviations. "
        "Isolation Forest provides independent multivariate corroboration."
    )

    intelligence_columns = st.columns(3)

    intelligence_columns[0].metric(
        "Detected events",
        len(process_events),
    )

    intelligence_columns[1].metric(
        "Fully ML-corroborated",
        int(
            (
                process_events["ml_corroboration_pct"] == 100
            ).sum()
        ),
    )

    intelligence_columns[2].metric(
        "Mean ML corroboration",
        f"{process_events['ml_corroboration_pct'].mean():.1f}%",
    )

    event_table = pd.DataFrame(
        {
            "Event": process_events["event_id"],
            "Time window": (
                process_events["start_time_h"].astype(str)
                + "–"
                + process_events["end_time_h"].astype(str)
                + " h"
            ),
            "Duration": (
                process_events["flagged_time_points"].astype(str)
                + " h"
            ),
            "Affected variables": process_events[
                "affected_variables"
            ].str.replace("_", " "),
            "ML corroboration": process_events[
                "ml_corroboration_pct"
            ].map(lambda value: f"{value:.1f}%"),
        }
    )

    st.dataframe(
        event_table,
        width="stretch",
        hide_index=True,
    )
    st.subheader("Process trajectories")

    variable_labels = {
        "ph": "pH",
        "dissolved_oxygen_pct": "Dissolved oxygen (%)",
        "temperature_c": "Temperature (°C)",
        "agitation_rpm": "Agitation (rpm)",
        "feed_rate_ml_h": "Feed rate (mL/h)",
    }

    selected_variable = st.selectbox(
        "Select a process variable",
        options=list(variable_labels),
        format_func=lambda column: variable_labels[column],
    )

    reference_data = data[
        data["batch_role"] == "reference"
    ]

    assessment_data = data[
        data["batch_role"] == "assessment"
    ]

    reference_summary = (
        reference_data
        .groupby("elapsed_time_h")[selected_variable]
        .agg(
            median="median",
            lower=lambda values: values.quantile(0.10),
            upper=lambda values: values.quantile(0.90),
        )
        .reset_index()
    )

    trajectory_figure = go.Figure()

    trajectory_figure.add_trace(
        go.Scatter(
            x=reference_summary["elapsed_time_h"],
            y=reference_summary["upper"],
            mode="lines",
            line={"width": 0},
            showlegend=False,
            hoverinfo="skip",
        )
    )

    trajectory_figure.add_trace(
        go.Scatter(
            x=reference_summary["elapsed_time_h"],
            y=reference_summary["lower"],
            mode="lines",
            line={"width": 0},
            fill="tonexty",
            fillcolor="rgba(8, 165, 181, 0.18)",
            name="Reference 10–90% band",
            hoverinfo="skip",
        )
    )

    trajectory_figure.add_trace(
        go.Scatter(
            x=reference_summary["elapsed_time_h"],
            y=reference_summary["median"],
            mode="lines",
            line={
                "color": "#082F63",
                "width": 2,
                "dash": "dash",
            },
            name="Reference median",
        )
    )

    trajectory_figure.add_trace(
        go.Scatter(
            x=assessment_data["elapsed_time_h"],
            y=assessment_data[selected_variable],
            mode="lines",
            line={
                "color": "#08A5B5",
                "width": 3,
            },
            name="Assessment batch",
        )
    )

    relevant_events = process_events[
        process_events["affected_variables"].str.contains(
            selected_variable,
            regex=False,
        )
    ]

    for _, event in relevant_events.iterrows():
        trajectory_figure.add_vrect(
            x0=event["start_time_h"],
            x1=event["end_time_h"],
            fillcolor="#F59E0B",
            opacity=0.18,
            line_width=0,
            annotation_text=event["event_id"],
            annotation_position="top left",
        )

    trajectory_figure.update_layout(
        xaxis_title="Elapsed time (h)",
        yaxis_title=variable_labels[selected_variable],
        hovermode="x unified",
        height=480,
        margin={"l": 20, "r": 20, "t": 60, "b": 20},
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "left",
            "x": 0,
        },
    )

    st.plotly_chart(
        trajectory_figure,
        width="stretch",
        config={
            "displaylogo": False,
            "scrollZoom": False,
        },
    )

    st.caption(
        "The shaded reference band represents the 10th–90th "
        "percentile range, not a specification or control limit. "
        "Amber regions identify detected process events affecting "
        "the selected variable."
    )
    st.subheader("Detector evaluation")

    evaluation_table = model_evaluation[
        ["model", "precision", "recall", "f1_score"]
    ].copy()

    for metric in ["precision", "recall", "f1_score"]:
        evaluation_table[metric] = evaluation_table[metric].map(
            lambda value: f"{value * 100:.1f}%"
        )

    evaluation_table = evaluation_table.rename(
        columns={
            "model": "Detector",
            "precision": "Precision",
            "recall": "Recall",
            "f1_score": "F1 score",
        }
    )

    st.dataframe(
        evaluation_table,
        width="stretch",
        hide_index=True,
    )

    st.info(
        "Performance is measured against known anomalies in the "
        "synthetic demonstration dataset. It does not represent "
        "validated performance on real manufacturing data."
    )

st.dataframe(
    data.head(50),
    width="stretch",
    hide_index=True,
)

st.caption(
    "The preview displays the first 50 rows. "
    "The complete validated dataset will be used for analysis."
)