"""
CLI script for running Reddit validation on subscription features.

Loads features from Google Trends metrics CSV, runs Reddit sentiment validation,
and saves results to CSV. Supports filtering by company or specific features to
manage API rate limits.

Product Analyst Context:
    Rate limits are the key constraint. Running validation on all 40+ features with
    8 keywords each = 320+ API calls. At 30-60 requests/minute, this takes 5-10 minutes
    with authenticated access, or 10-20 minutes with public JSON. The --companies and
    --features flags let you batch the work across multiple runs.

Usage Examples:
    # Validate all Netflix features
    python validate_features.py --companies "Netflix"
    
    # Validate multiple companies
    python validate_features.py --companies "Netflix,Spotify,Disney+"
    
    # Validate specific features (regardless of company)
    python validate_features.py --features "AI DJ,Password Sharing Crackdown"
    
    # Validate all features (long-running)
    python validate_features.py
"""

from dotenv import load_dotenv
import argparse
from pathlib import Path
from typing import List, Dict, Optional

import pandas as pd

from .reddit_validator import (
    RedditValidator,
    infer_company_from_keyword,
    enforce_feature_company_guard,
    generate_keywords,
)
from .reddit_config import FEATURE_OVERRIDES

# Load environment variables (for Reddit API credentials)
load_dotenv()


def validate_all_features_from_csv(
    metrics_path: str = "data/trends/MERGED_trends_data_PEAK_metrics.csv",
    raw_path: str = "data/trends/MERGED_trends_data.csv",
    companies_filter: Optional[List[str]] = None,
    feature_filter: Optional[List[str]] = None,
) -> None:
    """
    Validate all features listed in the trends metrics CSV.

    Workflow:
        1. Load trends metrics file (includes decay_rate_w4 / decay_rate_w8)
        2. Load raw trends file (includes 'keyword' text for company inference)
        3. For each feature:
            a. Determine company (from CSV, overrides, or keyword inference)
            b. Enforce FEATURE_COMPANY_GUARDS (prevent cross-product contamination)
            c. Apply filters (companies_filter, feature_filter)
            d. Generate Reddit search keywords (from overrides or auto-generate)
            e. Run validation (search Reddit, analyze sentiment, classify)
        4. Append/merge results into data/validation/reddit_validation_results.csv
        
    Why Two CSV Files:
        - metrics_path: Contains calculated metrics (decay_rate_w4, peak_interest, etc.)
        - raw_path: Contains original keywords used for Trends queries
        - We need keywords for company inference, but metrics for decay analysis
        
    Output Location:
        Results are saved to data/validation/reddit_validation_results.csv.
        If the file exists, new results are merged (deduplicating by feature + company,
        keeping the latest run). This allows incremental validation across multiple runs.

    Args:
        metrics_path: Path to metrics CSV with decay metrics and feature info.
        raw_path: Path to raw trends CSV (for 'keyword' text).
        companies_filter: Optional list of companies to include. If None, all companies
                         are processed.
        feature_filter: Optional list of specific feature names to include. If None,
                       all features are processed. Takes precedence over companies_filter.
                       
    Example:
        ```python
        # Validate only Netflix and Spotify
        validate_all_features_from_csv(
            companies_filter=["Netflix", "Spotify"]
        )
        
        # Validate specific features
        validate_all_features_from_csv(
            feature_filter=["AI DJ", "Password Sharing Crackdown"]
        )
        ```
    """
    validator = RedditValidator()

    # Load data
    metrics = pd.read_csv(metrics_path)
    raw = pd.read_csv(raw_path)

    # 🔍 Optional: filter by specific feature names (exact match)
    if feature_filter is not None and len(feature_filter) > 0:
        metrics = metrics[metrics["feature_name"].isin(feature_filter)]
        if metrics.empty:
            print(
                f"⚠️  No rows matched feature_filter={feature_filter}. "
                "Check spelling / capitalization vs metrics CSV."
            )
            return

    # Map feature_id -> a representative keyword string
    # We use this for company inference when CSV has missing/unknown company
    feature_keywords = (
        raw[["feature_id", "keyword"]]
        .drop_duplicates()
        .groupby("feature_id")["keyword"]
        .first()  # Take first keyword if multiple exist
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

        # --- Company Resolution (3-tier waterfall) ---
        
        # 1) Start from CSV company field
        company = csv_company

        # 2) If missing/Unknown, try FEATURE_OVERRIDES
        if (not company) or (str(company).lower() == "unknown"):
            if "company" in override:
                company = override["company"]
            else:
                # 3) Infer from raw keyword using pattern matching
                inferred = infer_company_from_keyword(keyword_from_raw)
                if inferred:
                    company = inferred

        # 2b) Guardrail: ensure risky features are attached to the right product
        # This prevents mixing YouTube TV with YouTube Premium, etc.
        if not enforce_feature_company_guard(feature_name, company):
            continue  # Skip this feature to avoid data contamination

        # Optional: filter by companies if provided
        if companies_filter is not None and company not in companies_filter:
            continue  # Skip features not in the company filter

        # Validate company can be mapped to a subreddit
        if (not company) or (company not in validator.subreddits):
            print(
                f"⚠️  Skipping '{feature_name}' "
                f"– missing or unmapped company (company='{company}', keyword='{keyword_from_raw}')."
            )
            continue

        # --- Get Search Decay ---
        
        # Prefer decay_rate_w4, fall back to decay_rate_w8
        # Both measure (peak - week_N) / peak, so higher = more decay
        decay = row.get("decay_rate_w4")
        if pd.isna(decay):
            decay = row.get("decay_rate_w8")

        # For very new features, both might be NaN (week_4/week_8 data not yet available)
        # We still want to pull Reddit data; classification will handle None gracefully
        if pd.isna(decay):
            decay = None

        # --- Determine Reddit Search Keywords ---
        
        # Use override keywords if defined (e.g., for "Password Sharing Crackdown")
        # Otherwise, auto-generate using feature name + company
        if "keywords" in override:
            reddit_keywords = override["keywords"]
        else:
            reddit_keywords = generate_keywords(feature_name, company)

        # --- Run Validation Pipeline ---
        
        result = validator.validate_feature(
            feature_name=feature_name,
            company=company,
            launch_date=launch_date,
            search_keywords=reddit_keywords,
            search_decay=float(decay) if decay is not None else None,
        )
        results.append(result)

    # --- Save Results ---
    
    if not results:
        print("⚠️  No features were validated. Check company mappings and filters.")
        return

    results_df = pd.DataFrame(results)
    out_path = Path("data/validation/reddit_validation_results.csv")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # If file exists, merge with existing results (avoid losing previous runs)
    # Keep latest run for each (feature_name, company) combination
    if out_path.exists():
        existing = pd.read_csv(out_path)
        combined = pd.concat([existing, results_df], ignore_index=True)
        # Drop duplicates by feature + company (keep latest run)
        combined = combined.drop_duplicates(
            subset=["feature_name", "company"], keep="last"
        )
        combined.to_csv(out_path, index=False)
        print(f"\n✅ Merged {len(results_df)} new results into existing file.")
    else:
        results_df.to_csv(out_path, index=False)
        print(f"\n✅ Saved {len(results_df)} results to new file.")

    # --- Print Summary ---
    
    print("\n" + "=" * 80)
    print("📊 VALIDATION SUMMARY (this run)")
    print("=" * 80)
    print(
        results_df[
            [
                "feature_name",
                "company",
                "search_decay",
                "sentiment_label",
                "total_mentions",
                "classification",
            ]
        ]
    )
    print(f"\n✅ Results saved to: {out_path}")
    
    # Print classification breakdown
    classification_counts = results_df["classification"].value_counts()
    print("\n📈 Classification Breakdown:")
    for classification, count in classification_counts.items():
        print(f"  {classification}: {count}")


def main() -> None:
    """
    Entry point for running Reddit validation from the command line.

    Supports optional filtering by company or feature to avoid hitting rate limits.
    
    Rate Limit Strategy:
        For large-scale validation, break work into batches:
        - Day 1: python validate_features.py --companies "Netflix,Spotify"
        - Day 2: python validate_features.py --companies "Disney+,YouTube TV"
        - Day 3: python validate_features.py --companies "Hulu,Apple Music"
        
        Results are automatically merged, so you won't lose previous runs.

    Examples:
        # Validate all Netflix features
        python validate_features.py --companies "Netflix"
        
        # Validate multiple companies in one run
        python validate_features.py --companies "Netflix,Spotify,Disney+"
        
        # Validate specific features by name
        python validate_features.py --features "AI DJ,Password Sharing Crackdown"
        
        # Validate everything (long-running, may hit rate limits)
        python validate_features.py
    """
    parser = argparse.ArgumentParser(
        description="Validate subscription features using Reddit sentiment analysis."
    )
    
    parser.add_argument(
        "--companies",
        type=str,
        default=None,
        help=(
            "Comma-separated list of companies to include "
            "(e.g. 'Netflix,Spotify,Disney+'). "
            "If omitted, all companies are processed. "
            "Use this to batch validation across multiple runs."
        ),
    )

    parser.add_argument(
        "--features",
        type=str,
        default=None,
        help=(
            "Comma-separated list of specific feature names to include "
            "(e.g. 'Premium Price Increase,Password Sharing Crackdown'). "
            "Feature names must match exactly as they appear in the metrics CSV. "
            "If provided, this filter takes precedence over --companies. "
            "If omitted, all features (or all features for --companies) are processed."
        ),
    )

    args = parser.parse_args()

    # Parse companies filter
    if args.companies:
        companies_filter = [c.strip() for c in args.companies.split(",") if c.strip()]
        print(f"🔧 Filtering to companies: {companies_filter}")
    else:
        companies_filter = None
        print("🔧 No company filter – processing all companies.")

    # Parse features filter
    if args.features:
        feature_filter = [f.strip() for f in args.features.split(",") if f.strip()]
        print(f"🔧 Filtering to features: {feature_filter}")
    else:
        feature_filter = None

    # Run validation
    validate_all_features_from_csv(
        companies_filter=companies_filter,
        feature_filter=feature_filter,
    )


if __name__ == "__main__":
    main()