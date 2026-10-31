"""
NorthStar Retail — Model Fairness & Slice Evaluation Gate
CS 401R Lab 4

This module verifies fairness and segment performance across customer slices
(specifically loyalty tiers: Bronze, Silver, Gold, Platinum).

Design:
  - Reads per-tier slice metrics from EVAL_METRICS_PATH (the same metrics dict
    emitted by churn_model.train() and saved to evaluation_metrics.json).
  - Evaluates recall@top10 disparity across loyalty tiers.
  - Flags (via visible pytest warnings) if the recall gap between the highest
    and lowest loyalty tier exceeds 10 percentage points (0.10).
  - DOES NOT BLOCK CI promotion on disparity: the requirement is that bias
    is prominently surfaced to the human approver in the Model Registry / CI logs,
    not that it silently breaks the pipeline.
"""

import json
import os
import warnings
from pathlib import Path

import pytest

RECALL_GAP_THRESHOLD = 0.10  # 10 percentage points


@pytest.fixture(scope="module")
def eval_metrics():
    """Load evaluation metrics containing per-slice performance."""
    metrics_path = os.environ.get("EVAL_METRICS_PATH", "/tmp/eval_metrics.json")
    path_obj = Path(metrics_path)

    if not path_obj.exists():
        # Fallback to local model metadata if available
        fallback = Path("model/model_metadata.json")
        if fallback.exists():
            path_obj = fallback
        else:
            pytest.fail(
                f"Evaluation metrics not found at {metrics_path}. Provide them "
                "with --eval-metrics-path or EVAL_METRICS_PATH."
            )

    with open(path_obj) as f:
        metrics = json.load(f)

    if not isinstance(metrics, dict):
        pytest.fail(f"Evaluation metrics in {path_obj} must be a JSON object")

    # If nested under evaluation_metrics (e.g. from model_metadata.json), unwrap it
    if "evaluation_metrics" in metrics and isinstance(metrics["evaluation_metrics"], dict):
        metrics = metrics["evaluation_metrics"]

    return metrics


class TestFairnessGate:
    """Fairness and slice quality evaluation gate."""

    def test_slice_metrics_exist(self, eval_metrics):
        """Assert that per-slice metrics were computed and recorded."""
        slices = eval_metrics.get("slices")
        assert isinstance(slices, dict) and len(slices) > 0, (
            "Evaluation metrics must include non-empty per-slice results under 'slices'. "
            "Ensure train() in models/churn/churn_model.py populates metrics['slices']."
        )

    def test_loyalty_tiers_evaluated(self, eval_metrics):
        """Verify that at least two loyalty tiers were evaluated with valid metrics."""
        slices = eval_metrics.get("slices", {})
        assert len(slices) >= 2, (
            f"Expected at least 2 slices for comparative evaluation, found {len(slices)}: {list(slices.keys())}"
        )

        for tier, data in slices.items():
            assert isinstance(data, dict), f"Slice data for '{tier}' must be a dictionary"
            assert "recall_top10" in data, f"Slice '{tier}' is missing 'recall_top10'"
            recall = data["recall_top10"]
            assert 0.0 <= recall <= 1.0, f"Slice '{tier}' recall {recall} outside valid range [0, 1]"

    def test_loyalty_tier_recall_gap(self, eval_metrics):
        """
        Flag (do not block) if recall gap between highest and lowest loyalty tier
        exceeds 10 percentage points (0.10).

        This test asserts validity of the metrics, computes the disparity gap,
        and triggers a prominent warning flag when the gap exceeds threshold.
        """
        slices = eval_metrics.get("slices", {})
        recalls = {
            tier: float(data["recall_top10"])
            for tier, data in slices.items()
            if isinstance(data, dict) and "recall_top10" in data
        }

        assert recalls, "No valid slice recall values found in eval_metrics['slices']"

        max_tier = max(recalls, key=recalls.get)
        min_tier = min(recalls, key=recalls.get)
        max_recall = recalls[max_tier]
        min_recall = recalls[min_tier]
        gap = max_recall - min_recall

        # Sanity check: gap is non-negative
        assert gap >= 0.0, f"Computed invalid negative gap: {gap}"

        # Flag (do not block) if disparity exceeds threshold
        if gap > RECALL_GAP_THRESHOLD:
            msg = (
                f"\n"
                f"=========================== FAIRNESS AUDIT FLAG ===========================\n"
                f"Recall@Top10 disparity between loyalty tiers exceeds {RECALL_GAP_THRESHOLD * 100:.1f} pp threshold!\n"
                f"  - Highest tier recall: '{max_tier}' = {max_recall:.4f} ({max_recall * 100:.1f}%)\n"
                f"  - Lowest tier recall:  '{min_tier}' = {min_recall:.4f} ({min_recall * 100:.1f}%)\n"
                f"  - Measured Recall Gap: {gap:.4f} ({gap * 100:.2f} percentage points)\n"
                f"  - Status: FLAGGED FOR REVIEW (Non-blocking warning for Model Approver)\n"
                f"==========================================================================="
            )
            warnings.warn(UserWarning(msg), stacklevel=2)

    def test_slice_audit_summary(self, eval_metrics):
        """
        Log per-slice audit metrics and flag any individual tier falling > 10pp below aggregate.
        """
        slices = eval_metrics.get("slices", {})
        flagged_tiers = [
            tier for tier, data in slices.items()
            if isinstance(data, dict) and data.get("flagged") is True
        ]

        if flagged_tiers:
            warnings.warn(
                UserWarning(
                    f"\n[FAIRNESS NOTICE] The following loyalty tiers were flagged with recall > 10pp "
                    f"below aggregate: {flagged_tiers}. Per-slice details: {slices}"
                ),
                stacklevel=2,
            )
