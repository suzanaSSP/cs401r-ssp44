# Lab 3: Evaluation Report (Task 1)

## Section 2: What your features bought you

### Model Performance Metrics

| Metric | Your value | Threshold | Status |
| :--- | :--- | :--- | :--- |
| **AUC-ROC (test set)** | 0.7764 | Report it — no fixed threshold | Passed |
| **Precision @ top 10%** | 0.6900 | ≥ 0.50 | Passed |
| **Recall @ top 10%** | 0.3136 | ≥ 0.25 | Passed |
| **AUC lift over recency baseline** | [0.0331, 0.0731] | 95% CI must exclude zero | Passed |

### Baseline Comparison & Lift
- **Baseline AUC (recency-only):** `0.7232`
- **Full Model AUC:** `0.7764`
- **95% Bootstrap Confidence Interval for Lift:** `[0.0331, 0.0731]`
- **Signal Interpretation:** The 95% confidence interval strictly excludes zero, proving statistically significant lift over the recency-only heuristic. Features capturing engagement cadence, frequency, and monetary spend carried authentic predictive signal beyond simple days-since-last-purchase.

### Slice Evaluation by Loyalty Tier
Referenced from `docs/lab3-evidence/slice-evaluation.csv`:
- **Weakest Tiers:** Gold has the lowest recall (13.46%, showing a >10 percentage point drop from the aggregate 31.36%), and Silver has the lowest slice AUC (0.6959).
- **Small Tier Consideration:** Platinum contains only 21 positive churners out of 307 validation customers, making the slice sample size statistically too small for isolated metric generalization without wide error bars.
