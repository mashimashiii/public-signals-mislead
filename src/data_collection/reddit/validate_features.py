"""
CLI script for running Reddit validation on subscription features.

Loads features from Google Trends metrics CSV, runs Reddit sentiment validation,
saves results to CSV. Supports filtering by company or specific features.

Usage:
    python validate_features.py --companies "Netflix"
    python validate_features.py --companies "Netflix,Spotify,Disney+"
    python validate_features.py --features "AI DJ,Password Sharing Crackdown"
    python validate_features.py  # All features (long-running)
"""

from dotenv import load_dotenv
import argparse
from pathlib import Path
from typing import List, Dict, Optional

import pandas as pd

from .reddit_validator import (
    RedditValidator, infer_company_from_keyword, enforce_feature_company_guard, generate_keywords
)
from .reddit_config import FEATURE_OVERRIDES

load_dotenv()


def validate_all_features_from_csv(
    metrics_path: str = "data/trends/MERGED_trends_data_PEAK_metrics.csv",
    raw_path: str = "data/trends/MERGED_trends_data.csv",
    companies_filter: Optional[List[str]] = None,
    feature_filter: Optional[List[str]] = None
) -> None:
    """
    Validate all features from trends metrics CSV.
    
    Workflow:
    1. Load metrics (decay rates) and raw (keywords for company inference)
    2. For each feature:
       a. Determine company (from CSV, overrides, or keyword inference)
       b. Enforce FEATURE_COMPANY_GUARDS (prevent cross-product contamination)
       c. Apply filters (companies_filter, feature_filter)
       d. Generate Reddit keywords
       e. Run validation (search Reddit, analyze sentiment, classify)
    3. Save results to data/validation/reddit_validation_results.csv
    
    Results are merged with existing file if it exists (deduplicating by feature+company).
    """
    validator = RedditValidator()

    # Load data
    metrics = pd.read_csv(metrics_path)
    raw = pd.read_csv(raw_path)

    # Optional: filter by specific feature names
    if feature_filter is not None and len(feature_filter) > 0:
        metrics = metrics[metrics["feature_name"].isin(feature_filter)]
        if metrics.empty:
            print(f"⚠ No rows matched feature_filter={feature_filter}")
            return

    # Map feature_id -> keyword for company inference
    feature_keywords = (
        raw[["feature_id", "keyword"]]
        .drop_duplicates()
        .groupby("feature_id")["keyword"]
        .first()
        .to_dict()
    )

    results: List[Dict] = []

    for _, row in metrics.iterrows():
        feature_id = row["feature_id"]
        feature_name = row["feature_name"]
        csv_company = row.get("company", "Unknown")
        launch_date = str(row["launch_date"])

        keyword_from_raw = feature_keywords.get(feature_id)
        override = FEATURE_OVERRIDES.get(feature_name, {})

        # Company resolution (3-tier waterfall)
        company = csv_company

        # If missing/Unknown, try overrides then keyword inference
        if (not company) or (str(company).lower() == "unknown"):
            if "company" in override:
                company = override["company"]
            else:
                inferred = infer_company_from_keyword(keyword_from_raw)
                if inferred:
                    company = inferred

        # Guardrail check
        if not enforce_feature_company_guard(feature_name, company):
            continue

        # Optional: filter by companies
        if companies_filter is not None and company not in companies_filter:
            continue

        # Validate company can be mapped to subreddit
        if (not company) or (company not in validator.subreddits):
            print(f"⚠ Skipping '{feature_name}' - missing/unmapped company (company='{company}')")
            continue

        # Get search decay
        decay = row.get("decay_rate_w4")
        if pd.isna(decay):
            decay = row.get("decay_rate_w8")
        if pd.isna(decay):
            decay = None

        # Determine Reddit keywords
        reddit_keywords = override.get("keywords") if "keywords" in override else generate_keywords(feature_name, company)

        # Run validation
        result = validator.validate_feature(
            feature_name=feature_name,
            company=company,
            launch_date=launch_date,
            search_keywords=reddit_keywords,
            search_decay=float(decay) if decay is not None else None
        )
        results.append(result)

    # Save results
    if not results:
        print("⚠ No features validated. Check company mappings and filters.")
        return

    results_df = pd.DataFrame(results)
    out_path = Path("data/validation/reddit_validation_results.csv")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Merge with existing if file exists
    if out_path.exists():
        existing = pd.read_csv(out_path)
        combined = pd.concat([existing, results_df], ignore_index=True)
        combined = combined.drop_duplicates(subset=["feature_name", "company"], keep="last")
        combined.to_csv(out_path, index=False)
        print(f"\n✓ Merged {len(results_df)} new results into existing file")
    else:
        results_df.to_csv(out_path, index=False)
        print(f"\n✓ Saved {len(results_df)} results to new file")

    # Summary
    print(f"\n{'='*80}")
    print("VALIDATION SUMMARY")
    print(f"{'='*80}")
    print(results_df[["feature_name", "company", "search_decay", "sentiment_label", "total_mentions", "classification"]])
    print(f"\n✓ Results saved to: {out_path}")
    
    classification_counts = results_df["classification"].value_counts()
    print("\nClassification:")
    for classification, count in classification_counts.items():
        print(f"  {classification}: {count}")


def main() -> None:
    """CLI entry point with optional company/feature filtering."""
    parser = argparse.ArgumentParser(description="Validate subscription features using Reddit sentiment")
    
    parser.add_argument(
        "--companies", type=str, default=None,
        help="Comma-separated companies (e.g. 'Netflix,Spotify,Disney+'). Use for batching across multiple runs."
    )

    parser.add_argument(
        "--features", type=str, default=None,
        help="Comma-separated feature names (e.g. 'Premium Price Increase,AI DJ'). Takes precedence over --companies."
    )

    args = parser.parse_args()

    # Parse filters
    companies_filter = None
    if args.companies:
        companies_filter = [c.strip() for c in args.companies.split(",") if c.strip()]
        print(f"🔧 Filtering to companies: {companies_filter}")
    else:
        print("🔧 No company filter - processing all companies")

    feature_filter = None
    if args.features:
        feature_filter = [f.strip() for f in args.features.split(",") if f.strip()]
        print(f"🔧 Filtering to features: {feature_filter}")

    # Run validation
    validate_all_features_from_csv(
        companies_filter=companies_filter,
        feature_filter=feature_filter
    )


if __name__ == "__main__":
    main()
