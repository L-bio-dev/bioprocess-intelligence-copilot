# Project Scope

## 1. What is this project?

Bioprocess Intelligence Copilot is a web application that helps users review fed-batch bioprocess data.

A fed-batch process starts with an initial culture volume. More nutrients are then added during the process without removing the full culture.

The application will compare:

* several **reference batches**, which represent the expected process behaviour;
* one **assessment batch**, which is the batch the user wants to investigate.

The application will highlight unusual data and organise the available evidence. It will support the engineer, but the engineer will always make the final decision.

## 2. How will the application be used?

The first version will analyse uploaded data after a batch has been completed. It will not connect directly to bioreactor sensors.

Users will upload synthetic or non-confidential data and use the application to:

* check data quality;
* compare batch profiles;
* identify unusual observations;
* review possible explanations;
* decide what should be checked next.

This project is an educational and portfolio prototype. It is not a validated industrial system.

It must not be used for:

* automatic process control;
* official GMP decisions;
* batch release;
* official deviation investigations;
* confirmed root-cause analysis;
* regulatory submissions.

GMP means **Good Manufacturing Practice**, the regulated quality system used to manufacture medicines consistently and safely.

## 3. Who is the user?

The main user is a bioprocess engineer, scientist, or technical student who wants to review comparable fed-batch runs.

The Copilot may:

* describe what it observes;
* show the measurements supporting an observation;
* flag unusual data;
* suggest possible explanations;
* state which information is missing;
* suggest additional checks.

The Copilot must not claim that a possible explanation is a confirmed cause.

If there is not enough information, it must say so clearly.

## 4. What data will be used?

Users will upload a CSV file.

CSV stands for **comma-separated values**. It is a simple table format that can be opened with programs such as Excel and read by Python.

The dataset will contain:

* batch identifier;
* elapsed process time;
* pH;
* dissolved oxygen;
* temperature;
* agitation rate;
* feed rate.

These five measurements will be called **selected process variables**.

We will not automatically call them **critical process parameters**, or CPPs. A process parameter can only be considered critical when there is process-specific evidence showing that its variation can affect a critical quality attribute of the product.

The public demo will use synthetic data created specifically for this project.

Users will be warned not to upload:

* confidential data;
* proprietary company data;
* personal data;
* real GMP production data.

The application will not be designed to save uploaded datasets permanently.

## 5. What will the application do?

The first version will follow this workflow:

1. The user uploads a CSV file.
2. The application checks whether the required columns and values are present.
3. It reports missing, duplicated, invalid, or inconsistent data.
4. It checks whether the batches are suitable for comparison.
5. It displays the process-variable profiles over time.
6. It compares the assessment batch with the reference batches.
7. It identifies unusual observations.
8. It prepares a structured summary for the engineer.
9. The engineer reviews the evidence and makes the final decision.

The reference batches will be used to create **reference bands**. These bands describe the behaviour observed in the reference data.

A reference band is not a specification limit. It does not prove whether a batch is acceptable or unacceptable.

## 6. How will the Copilot communicate?

Each assessment will contain six parts:

1. **Observation** — what the application detected;
2. **Supporting evidence** — the relevant measurements;
3. **Possible interpretation** — a hypothesis that could explain the observation;
4. **Missing evidence** — information needed to evaluate that hypothesis;
5. **Suggested checks** — possible next actions for the engineer;
6. **Human decision** — the conclusion entered by the user.

This structure keeps measured evidence separate from interpretation.

## 7. How will AI be used?

The first analytical layer will use simple and transparent statistics.

After this baseline is working, we plan to add an Isolation Forest model.

Isolation Forest is a machine-learning method for anomaly detection. An anomaly is an observation that appears unusual compared with the reference data.

The model can work without a traditional dataset containing labelled examples of every good and bad condition. It will analyse combinations of process variables and assign an anomaly score.

However, an unusual observation is not automatically a process failure. The model will not identify a confirmed root cause.

Isolation Forest also does not automatically understand the full history of a time series. For example, it does not directly understand that dissolved oxygen has been decreasing continuously for four hours. Additional time-based features would be needed for this type of analysis.

The application will therefore combine:

* transparent statistical comparisons;
* machine-learning anomaly scores;
* controlled explanations linked to visible evidence;
* clear refusal when the available data are insufficient.

The MVP will not require a paid external language-model API.

## 8. When will the MVP be successful?

The MVP will be considered successful when it can:

* run on the developer’s computer;
* run as a public web application;
* analyse the documented synthetic dataset;
* accept an external CSV with the correct format;
* reject invalid or insufficient data safely;
* compare one assessment batch with multiple reference batches;
* show clear statistical and machine-learning evidence;
* separate observations from hypotheses;
* leave the final decision to the human user;
* reproduce the same analysis using the documented code and software versions.

Tests performed with synthetic anomalies will measure performance only on the synthetic dataset. They will not prove performance on real industrial anomalies.

## 9. How will decisions be documented?

Important project decisions will use one of three labels:

* **Source-supported** — supported by an identified scientific or official source;
* **Engineering design choice** — selected because it fits the goal and limits of this project;
* **MVP assumption** — a temporary assumption that must be tested or reviewed later.

For example, the exact minimum number of reference batches and the maximum acceptable percentage of missing data have not yet been validated. When selected, they will initially be documented as MVP assumptions.

## 10. Main references

* [ICH Q8(R2): Pharmaceutical Development](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/q8r2-pharmaceutical-development)
* [FDA: Process Analytical Technology Framework](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/pat-framework-innovative-pharmaceutical-development-manufacturing-and-quality-assurance)
* [FDA: AI Supporting Regulatory Decision-Making](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/considerations-use-artificial-intelligence-support-regulatory-decision-making-drug-and-biological)
* [EMA and FDA: Principles for AI in Medicine Development](https://www.ema.europa.eu/en/about-us/how-we-work/data-regulation-big-data-other-sources/artificial-intelligence)
* [scikit-learn: Isolation Forest](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.IsolationForest.html)
