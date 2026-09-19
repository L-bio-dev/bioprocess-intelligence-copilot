# Event explanations

The app can describe each detected process event in plain English.
The user selects an event below the event table.

The explanation shows:

- the first and last flagged measurement times;
- how many time points the robust detector flagged;
- the variables flagged and whether their flagged values were above, below,
  or on both sides of the reference median;
- the largest absolute robust Z-score for each flagged variable, its time,
  the measured value and the reference median at that same time;
- how many event time points were also flagged by Isolation Forest.

Directions and peak scores use only measurements flagged by the robust detector
within the selected event. Other measurements do not enter these descriptions.
An hour with multiple flagged variables counts once in detector agreement.
An ML-only flag cannot create a process event or a corresponding explanation.

The sentences are built from fixed wording and calculated results. This feature
does not call a language model or an external API. Using AI during development
is separate from how these explanations are produced when the app runs.

Detector agreement is not a probability of process failure. The explanations
do not identify causes, make batch-release decisions or describe behaviour
between measurement times. Sparse sampling can leave long gaps in an event
window; the window is not a claim about the true duration of a deviation.
