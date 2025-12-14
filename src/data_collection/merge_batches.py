"""
Merge batch-level Google Trends files into a single dataset.

Merges:
- data/trends/full_trends_data_batch_*.csv → MERGED_trends_data.csv
- data/trends/full_decay_metrics_batch_*.csv → MERGED_decay_metrics.csv

If a feature appears in 'batch_extended_extreme_peaks' files, those rows REPLACE
any rows for the same feature from other batches.

Usage: python src/data_collection/merge_batches.py
"""

from pathlib import Path
from typing import List

import pandas as pd


DATA_DIR = Path("data/trends")
EXTENDED_TAG = "extended_extreme_peaks"


def _load_with_source(files: List[Path]) -> pd.DataFrame:
    """Load CSVs and tag each row with its source filename."""
    dfs = []
    for f in files:
        df = pd.read_csv(f)
        df["source_file"] = f.name
        dfs.append(df)
    if not dfs:
        return pd.DataFrame()
    return pd.concat(dfs, ignore_index=True)


def merge_trends() -> pd.DataFrame:
    """Merge all full_trends_data_batch_* files with extended-batch override."""
    pattern = "full_trends_data_batch_*.csv"
    trend_files = sorted(DATA_DIR.glob(pattern))

    if not trend_files:
        raise FileNotFoundError(f"No trend files matching {pattern} in {DATA_DIR}")

    print("🧩 Merging trends files:")
    for f in trend_files:
        print(f"   - {f.name}")

    trends = _load_with_source(trend_files)

    if trends.empty:
        raise ValueError("Loaded trends data is empty")

    if "feature_id" not in trends.columns:
        raise KeyError("Expected column 'feature_id' in trends files")

    # Extended batch override
    extended_mask = trends["source_file"].str.contains(EXTENDED_TAG, na=False)
    extended_ids = trends.loc[extended_mask, "feature_id"].unique()

    print(f"\n🔍 Found {len(extended_ids)} feature(s) in extended batch: {extended_ids.tolist()}")

    if len(extended_ids) > 0:
        before_rows = len(trends)
        trends = trends[(~trends["feature_id"].isin(extended_ids)) | extended_mask].copy()
        after_rows = len(trends)
        print(f"   → Dropped {before_rows - after_rows} shorter-window rows for extended features")

    # Sort and clean
    if "date" in trends.columns:
        trends = trends.sort_values(["feature_id", "date"]).reset_index(drop=True)
    else:
        trends = trends.sort_values(["feature_id"]).reset_index(drop=True)

    trends.drop(columns=["source_file"], inplace=True)

    out_path = DATA_DIR / "MERGED_trends_data.csv"
    trends.to_csv(out_path, index=False)
    print(f"\n✓ Saved merged trends to: {out_path}")
    print(f"   Total rows: {len(trends)}, Features: {trends['feature_id'].nunique()}")

    return trends


def merge_metrics() -> pd.DataFrame:
    """Merge all full_decay_metrics_batch_* files with extended batch override."""
    pattern = "full_decay_metrics_batch_*.csv"
    metric_files = sorted(DATA_DIR.glob(pattern))

    if not metric_files:
        raise FileNotFoundError(f"No metrics files matching {pattern} in {DATA_DIR}")

    print("\n🧩 Merging metrics files:")
    for f in metric_files:
        print(f"   - {f.name}")

    metrics = _load_with_source(metric_files)

    if metrics.empty:
        raise ValueError("Loaded metrics data is empty")

    if "feature_id" not in metrics.columns:
        raise KeyError("Expected column 'feature_id' in metrics files")

    extended_mask = metrics["source_file"].str.contains(EXTENDED_TAG, na=False)
    extended_ids = metrics.loc[extended_mask, "feature_id"].unique()

    print(f"\n🔍 Found {len(extended_ids)} feature(s) in extended metrics batch: {extended_ids.tolist()}")

    if len(extended_ids) > 0:
        before_rows = len(metrics)
        metrics = metrics[(~metrics["feature_id"].isin(extended_ids)) | extended_mask].copy()
        after_rows = len(metrics)
        print(f"   → Dropped {before_rows - after_rows} older metric rows for extended features")

    # Deduplicate (keep last/extended)
    metrics = (
        metrics.sort_values(["feature_id", "source_file"])
        .drop_duplicates(subset=["feature_id"], keep="last")
        .reset_index(drop=True)
    )

    metrics.drop(columns=["source_file"], inplace=True)

    out_path = DATA_DIR / "MERGED_decay_metrics.csv"
    metrics.to_csv(out_path, index=False)
    print(f"\n✓ Saved merged metrics to: {out_path}")
    print(f"   Total features: {metrics['feature_id'].nunique()}")

    return metrics


def main() -> None:
    print("📦 Starting batch merge\n")
    merge_trends()
    merge_metrics()
    print("\n🎉 Merging complete. Run recalculate_with_peaks.py on MERGED_trends_data.csv")


if __name__ == "__main__":
    main()
