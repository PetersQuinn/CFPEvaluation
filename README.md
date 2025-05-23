# Evaluation of the College Football Playoff Perception Bias

This repository accompanies the paper **"Perception vs. Performance: Quantifying Decision Accuracy in the College Football Playoff"** by Quinton Peters. It includes Python simulation code and visualizations designed to evaluate the influence of preseason and weekly perception-based biases on the College Football Playoff (CFP) rankings.

The project compares two committee scoring approaches (Standard vs. Harsher) across a full FBS model of 134 teams over 12 weeks and investigates how ranking systems reward perceived strength versus on-field performance.

---

## Contents

* `standard_committee_simulation.py`
  Implements the baseline CFP points system, reflecting the traditional approach to ranking teams based on a blend of perception and results.

* `harsher_committee_simulation.py`
  Uses a modified points system that rewards wins over strong opponents more aggressively and penalizes losses more severely, emphasizing field performance over narrative.

* `Evaluation_of_the_CFP_Perception_Bug_Final.pdf`
  Full research paper detailing the methodology, analysis, visualizations, and qualitative insights from both simulation models.

---

## Objectives

This project explores:

* How preseason biases distort CFP rankings.
* Differences in outcomes between conservative and aggressive ranking models.
* Trade-offs between ranking stability, volatility, accuracy, and viewer engagement.
* Quantitative metrics such as:

  * Average and maximum rank discrepancies
  * Largest week-to-week rank changes
  * Metrics specifically focused on the CFP Top 25

---

## Technologies Used

* Python 3
* Matplotlib
* NumPy
* `random`, `copy`, `itertools`, `collections.Counter`

---

## How to Run

Each script can be executed independently to simulate multiple seasons and generate statistical summaries with plots.

```bash
python standard_committee_simulation.py
python harsher_committee_simulation.py
```

Both scripts simulate 100 seasons with 134 teams and a 12-week schedule.

---

## Key Metrics Tracked

Each script calculates and visualizes the following metrics per week:

* Average absolute difference between CFP and true rank (`AvgDiff`)
* Maximum difference (`MaxDiff`)
* Largest weekly rise/fall in rankings (`MaxRise`, `MaxFall`)
* `AvgDiff` and `MaxDiff` limited to Top-25 CFP teams

These are plotted over time to observe how committee philosophy affects convergence, volatility, and accuracy.

---

## Author

**Quinton Peters**
B.S.E. Candidate, Risk, Data, and Financial Engineering
Duke University
Date: January 16, 2025
