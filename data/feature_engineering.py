"""Pandas implementation of NorthStar's customer-level churn features.

The functions in this module operate on processed, transaction-grain data and
return at most one row per customer. ``snapshot_date`` is the feature cutoff:
transactions after it are excluded from predictors to prevent label leakage.
"""

from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd


N_CATEGORIES = 8
NO_PURCHASE_RECENCY_DAYS = 999
HOLDOUT_END_DATE = pd.Timestamp("2026-06-30")


def _as_timestamp(value) -> pd.Timestamp:
    """Return a normalized, timezone-naive date for date comparisons."""
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is not None:
        timestamp = timestamp.tz_convert(None)
    return timestamp.normalize()


def _transactions_frame(transactions: pd.DataFrame) -> pd.DataFrame:
    if not isinstance(transactions, pd.DataFrame):
        raise TypeError("transactions must be a pandas DataFrame")
    if "customer_id" not in transactions.columns:
        raise ValueError("transactions must include customer_id")

    frame = transactions.copy()
    if "purchase_date" in frame.columns:
        frame["purchase_date"] = pd.to_datetime(
            frame["purchase_date"], errors="coerce", utc=True
        ).dt.tz_convert(None).dt.normalize()
    return frame


def _customer_ids(
    transactions: pd.DataFrame,
    customers: pd.DataFrame | pd.Series | Iterable[str] | None = None,
) -> pd.DataFrame:
    """Build a stable one-row-per-customer roster for aggregate results."""
    if customers is None:
        values = transactions["customer_id"].dropna().drop_duplicates()
        return pd.DataFrame({"customer_id": values.to_list()})
    if isinstance(customers, pd.DataFrame):
        if "customer_id" not in customers.columns:
            raise ValueError("customers must include customer_id")
        values = customers["customer_id"]
    elif isinstance(customers, pd.Series):
        values = customers
    else:
        values = pd.Series(list(customers), dtype="object")
    return pd.DataFrame({"customer_id": values.dropna().drop_duplicates().to_list()})


def _as_of(frame: pd.DataFrame, snapshot_date) -> tuple[pd.DataFrame, pd.Timestamp]:
    if "purchase_date" not in frame.columns:
        raise ValueError("transactions must include purchase_date")
    cutoff = _as_timestamp(snapshot_date)
    history = frame.loc[
        frame["purchase_date"].notna() & (frame["purchase_date"] <= cutoff)
    ].copy()
    return history, cutoff


def _complete_aggregate(
    roster: pd.DataFrame,
    aggregate: pd.DataFrame,
    columns: list[str],
    fill_values: dict[str, float],
) -> pd.DataFrame:
    result = roster.merge(aggregate, on="customer_id", how="left", validate="one_to_one")
    for column in columns:
        result[column] = result[column].fillna(fill_values[column])
    return result


def compute_recency_features(
    transactions: pd.DataFrame,
    snapshot_date,
    customers: pd.DataFrame | pd.Series | Iterable[str] | None = None,
) -> pd.DataFrame:
    """Compute days since last purchase and customer tenure.

    Customers with no qualifying purchases get recency 999 and tenure 0.
    ``customers`` may provide a roster so those customers are retained in the
    result even when ``transactions`` is empty or contains no matching rows.
    """
    frame = _transactions_frame(transactions)
    history, cutoff = _as_of(frame, snapshot_date)
    roster = _customer_ids(frame, customers)

    if history.empty:
        aggregate = pd.DataFrame(columns=[
            "customer_id", "days_since_last_purchase", "customer_tenure_days"
        ])
    else:
        dates = history.groupby("customer_id", as_index=False, sort=False).agg(
            first_purchase=("purchase_date", "min"),
            last_purchase=("purchase_date", "max"),
        )
        dates["days_since_last_purchase"] = (
            cutoff - dates["last_purchase"]
        ).dt.days.astype(float)
        dates["customer_tenure_days"] = (
            cutoff - dates["first_purchase"]
        ).dt.days.astype(float)
        aggregate = dates[[
            "customer_id", "days_since_last_purchase", "customer_tenure_days"
        ]]

    return _complete_aggregate(
        roster,
        aggregate,
        ["days_since_last_purchase", "customer_tenure_days"],
        {
            "days_since_last_purchase": NO_PURCHASE_RECENCY_DAYS,
            "customer_tenure_days": 0,
        },
    )


def compute_frequency_features(
    transactions: pd.DataFrame,
    snapshot_date,
    customers: pd.DataFrame | pd.Series | Iterable[str] | None = None,
) -> pd.DataFrame:
    """Count transactions in the 30-, 90-, and 180-day windows before cutoff."""
    frame = _transactions_frame(transactions)
    history, cutoff = _as_of(frame, snapshot_date)
    roster = _customer_ids(frame, customers)
    columns = [
        "purchase_frequency_30d",
        "purchase_frequency_90d",
        "purchase_frequency_180d",
    ]

    aggregate = pd.DataFrame(columns=["customer_id", *columns])
    if not history.empty:
        counts = history[["customer_id", "purchase_date"]].copy()
        for days, column in ((30, columns[0]), (90, columns[1]), (180, columns[2])):
            in_window = counts["purchase_date"] > cutoff - pd.Timedelta(days=days)
            counts[column] = in_window.astype(int)
        aggregate = counts.groupby("customer_id", as_index=False, sort=False)[
            columns
        ].sum()

    return _complete_aggregate(roster, aggregate, columns, {c: 0 for c in columns})


def compute_monetary_features(
    transactions: pd.DataFrame,
    snapshot_date,
    customers: pd.DataFrame | pd.Series | Iterable[str] | None = None,
) -> pd.DataFrame:
    """Compute lifetime value, 90-day spend, average order value, and basket size."""
    frame = _transactions_frame(transactions)
    history, cutoff = _as_of(frame, snapshot_date)
    roster = _customer_ids(frame, customers)
    columns = [
        "avg_order_value",
        "total_spend_90d",
        "total_lifetime_value",
        "avg_basket_size_6m",
    ]

    aggregate = pd.DataFrame(columns=["customer_id", *columns])
    if not history.empty:
        history["_order_value"] = pd.to_numeric(
            history.get("order_value", pd.Series(index=history.index, dtype=float)),
            errors="coerce",
        )
        history["_num_items"] = pd.to_numeric(
            history.get("num_items", pd.Series(index=history.index, dtype=float)),
            errors="coerce",
        )
        history["_recent_90d_value"] = history["_order_value"].where(
            history["purchase_date"] > cutoff - pd.Timedelta(days=90), 0.0
        )
        basket_180 = history.loc[
            history["purchase_date"] > cutoff - pd.Timedelta(days=180)
        ]

        aggregate = history.groupby("customer_id", as_index=False, sort=False).agg(
            avg_order_value=("_order_value", "mean"),
            total_spend_90d=("_recent_90d_value", "sum"),
            total_lifetime_value=("_order_value", "sum"),
        )
        basket = basket_180.groupby("customer_id", as_index=False, sort=False).agg(
            avg_basket_size_6m=("_num_items", "mean")
        )
        aggregate = aggregate.merge(basket, on="customer_id", how="left", validate="one_to_one")

    return _complete_aggregate(roster, aggregate, columns, {c: 0.0 for c in columns})


def compute_behavioral_features(
    transactions: pd.DataFrame,
    customers: pd.DataFrame | pd.Series | Iterable[str] | None = None,
) -> pd.DataFrame:
    """Compute category diversity and the online share of a customer's orders."""
    frame = _transactions_frame(transactions)
    roster = _customer_ids(frame, customers)
    columns = ["category_diversity_score", "online_to_store_ratio"]

    aggregate = pd.DataFrame(columns=["customer_id", *columns])
    if not frame.empty:
        category_counts = pd.DataFrame(columns=["customer_id", "_category_count"])
        if "product_category" in frame.columns:
            valid = frame.loc[
                frame["product_category"].notna()
                & (frame["product_category"] != "unknown"),
                ["customer_id", "product_category"],
            ]
            category_counts = valid.groupby("customer_id", as_index=False, sort=False)[
                "product_category"
            ].nunique().rename(columns={"product_category": "_category_count"})

        behavior = frame.groupby("customer_id", as_index=False, sort=False).size()
        behavior = behavior.rename(columns={"size": "_orders"})
        if "channel" in frame.columns:
            online = frame.assign(
                _online=frame["channel"].eq("online").astype(int)
            ).groupby("customer_id", as_index=False, sort=False)["_online"].sum()
        else:
            online = pd.DataFrame(columns=["customer_id", "_online"])

        aggregate = behavior.merge(category_counts, on="customer_id", how="left")
        aggregate = aggregate.merge(online, on="customer_id", how="left")
        aggregate["category_diversity_score"] = (
            aggregate["_category_count"].fillna(0) / N_CATEGORIES
        ).clip(upper=1.0)
        aggregate["online_to_store_ratio"] = (
            aggregate["_online"].fillna(0) / aggregate["_orders"].replace(0, np.nan)
        ).fillna(0.0)
        aggregate = aggregate[["customer_id", *columns]]

    return _complete_aggregate(roster, aggregate, columns, {c: 0.0 for c in columns})


def build_churn_feature_set(
    customers: pd.DataFrame,
    transactions: pd.DataFrame,
    snapshot_date,
) -> pd.DataFrame:
    """Return one complete churn feature row per customer in ``customers``.

    Predictors use transactions on or before ``snapshot_date``. If the roster
    lacks ``churn_label``, derive it from purchases in the holdout period up to
    June 30, 2026, matching the Lab 2 Glue job's temporal split.
    """
    if not isinstance(customers, pd.DataFrame) or "customer_id" not in customers.columns:
        raise ValueError("customers must be a DataFrame containing customer_id")

    roster = customers.drop_duplicates("customer_id", keep="first").copy()
    frame = _transactions_frame(transactions)
    if "purchase_date" not in frame.columns:
        raise ValueError("transactions must include purchase_date")
    cutoff = _as_timestamp(snapshot_date)
    history = frame.loc[
        frame["purchase_date"].notna()
        & (frame["purchase_date"] <= cutoff)
        & frame["customer_id"].notna()
    ].copy()

    pieces = [
        compute_recency_features(history, cutoff, roster),
        compute_frequency_features(history, cutoff, roster),
        compute_monetary_features(history, cutoff, roster),
        compute_behavioral_features(history, roster),
    ]
    result = roster
    for piece in pieces:
        # Replace any same-named roster columns with the calculated predictors.
        overlaps = [c for c in piece.columns if c != "customer_id" and c in result.columns]
        if overlaps:
            result = result.drop(columns=overlaps)
        result = result.merge(piece, on="customer_id", how="left", validate="one_to_one")

    lifetime = result["total_lifetime_value"]
    if "loyalty_tier" not in result.columns:
        result["loyalty_tier"] = np.select(
            [lifetime < 500, lifetime < 2000, lifetime < 5000],
            ["Bronze", "Silver", "Gold"],
            default="Platinum",
        )

    if "churn_label" not in result.columns:
        holdout = frame.loc[
            frame["purchase_date"].notna()
            & (frame["purchase_date"] > cutoff)
            & (frame["purchase_date"] <= HOLDOUT_END_DATE)
        ]
        holdout_customers = set(holdout["customer_id"].dropna().unique())
        result["churn_label"] = (~result["customer_id"].isin(holdout_customers)).astype(int)

    days = result["days_since_last_purchase"].astype(float)
    freq30 = result["purchase_frequency_30d"].astype(float)
    high = 0.7 + np.minimum(0.3, (days - 60.0) / 100.0 * 0.3)
    medium = 0.4 + np.minimum(0.3, (days - 30.0) / 30.0 * 0.3)
    low = np.minimum(0.4, (days / 30.0) * 0.4)
    result["churn_risk_score"] = np.select(
        [(days > 60) & (freq30 == 0), days > 30],
        [high, medium],
        default=low,
    ).clip(0.0, 1.0)

    return result
