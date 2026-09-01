# Bioprocess Intelligence Copilot

I am a Biotechnology Engineering student at Absalon University. I built this project to apply data analysis and AI-assisted development to a bioprocess example.

The app compares one bioreactor run with a group of reference runs. It shows the process measurements over time and highlights differences that may need further investigation.

This is a student portfolio project. The built-in demonstration uses simulated data, and the application is not a validated manufacturing tool.

## How I built it

I developed this project through vibe coding with AI. AI helped me plan the application, generated much of the Python code, and supported troubleshooting and technical explanations. I did not write every function from scratch.

My contribution was to define what the application should do, evaluate the proposed changes, run the tests, inspect the results, solve problems during development, and manage the project using GitHub and Codespaces.

AI was used to support the development process. The application itself is not a chatbot and does not use a language model to analyse the data. Its analysis is based on statistical calculations and an Isolation Forest model.

## What the app compares

A batch means one run of the bioreactor process, with measurements collected over time.

The assessment batch is the batch being checked. The reference batches are the runs used for comparison. These names describe their role in the analysis: they do not automatically mean “bad batch” and “good batches”.

The app compares measurements at the same elapsed process time. For example, dissolved oxygen at hour 100 in the assessment batch is compared with dissolved oxygen at hour 100 in the reference batches.

The five process variables are:

* pH;
* dissolved oxygen;
* temperature;
* agitation;
* feed rate.

## How the analysis works

The user can select the built-in demonstration or upload a CSV file.

Before running the analysis, the app checks the dataset for problems such as missing columns, invalid values, duplicate measurements and inconsistent batch structure. If it finds a blocking problem, the analysis stops and the error is displayed.

The app then uses two detection methods.

### Robust Z-score

The Robust Z-score checks each process variable separately. At every elapsed time, it compares the assessment value with the reference values using the median and Median Absolute Deviation, or MAD.

This method identifies which variable is unusually high or low compared with the reference batches.

### Isolation Forest

Isolation Forest is a machine-learning method for anomaly detection. It examines the five process variables together and looks for unusual combinations of measurements.

It provides a second view of the data, but it does not identify a confirmed process failure or root cause.

### Comparing the detectors

The app shows whether a time point was flagged by both methods, by only one method, or by neither.

Consecutive points flagged by the Robust Z-score method are grouped into process events. Points flagged only by Isolation Forest are displayed separately for review and are not automatically added to the event table.

For each event, ML corroboration shows the percentage of its flagged time points that were also flagged by Isolation Forest. It is not a confidence score or a probability that the batch has failed.

## Charts and outputs

The interactive charts show:

* the assessment batch;
* the reference median;
* the reference 10th–90th percentile range;
* the time windows of detected events.

The percentile range describes the reference data. It is not a specification, an acceptance limit or the threshold used by the detector.

The app also shows a summary of the detected events and allows the user to download:

* the process-event summary;
* the hourly detector results.

Both outputs are provided as CSV files.

## Demonstration dataset

The built-in demonstration contains:

* 20 reference batches;
* 1 assessment batch;
* 241 hourly measurements per batch, from hour 0 to hour 240;
* 5 process variables.

Two known changes were deliberately added to the assessment batch:

* From hour 120 to hour 144, the feed rate was reduced to 65% of its original value.
* From hour 170 to hour 190, dissolved oxygen was reduced by 12 percentage points and agitation was increased by 45 rpm.

These changes affect 46 time points.

The Robust Z-score method found all 46 affected points without additional flags. Isolation Forest found 42 of them, missed 4 and flagged 10 other points.

These results only describe the simulated demonstration. They do not prove that the methods will perform equally well on real manufacturing data.

## Uploading data

Users can upload a CSV file of up to 25 MB.

The dataset must contain:

* exactly one assessment batch;
* at least ten reference batches;
* the five required process variables;
* matching measurement times across batches.

The complete column names and validation rules are documented in `docs/data_contract.md`.

Users must not upload confidential, proprietary, personal or real GMP production data.

## Run the project in GitHub Codespaces

The project was developed with Python 3.12.

Create and activate the virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

Install the dependencies:

```bash
python -m pip install -r requirements.txt
```

Run the automated tests:

```bash
python -m pytest -q
```

Start the Streamlit application:

```bash
streamlit run app.py
```

Open the forwarded Streamlit port in the browser and keep the terminal running while using the application.

## Limitations

A detected anomaly means that a measurement should be reviewed. It does not prove that the batch has failed.

The application cannot determine root cause, product quality, patient impact or batch acceptability.

Reference batches must come from comparable processes and use consistent units. Passing the input validation checks does not prove that the selected batches are scientifically suitable for comparison.

The application has only been evaluated with simulated data. Passing the software tests does not demonstrate validated performance on real manufacturing data.

The project is not validated for GMP use, automatic process control, batch release, official deviation investigations or regulatory decisions.

## Tools used

Python, pandas, NumPy, scikit-learn, Plotly, Streamlit, pytest, GitHub Codespaces and AI.

## License

The project is provided under the terms contained in the `LICENSE` file.
