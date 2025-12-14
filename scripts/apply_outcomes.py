"""
Apply known business outcomes to labeled features CSV.

Run once to populate labeled_features.csv with verified outcomes from config/outcomes.py.

Usage: python scripts/apply_outcomes.py
"""

import pandas as pd
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from config.outcomes import KNOWN_OUTCOMES, get_outcome, get_feature_type


def apply_outcomes_to_csv():
    """
    Apply known business outcomes from config to the labeled features CSV.
    Updates columns for success/failure labels and metrics.
    """
    csv_path = PROJECT_ROOT / 'data' / 'validation' / 'labeled_features.csv'
    df = pd.read_csv(csv_path)
    
    print(f"Loaded {len(df)} features from {csv_path.relative_to(PROJECT_ROOT)}")
    print(f"Companies: {', '.join(df['company'].unique())}\n")
    
    # Apply outcomes from config
    df['known_outcome'] = df['feature_name'].apply(
        lambda x: get_outcome(x).get('outcome', 'UNKNOWN') if get_outcome(x) else 'UNKNOWN'
    )
    df['outcome_metric'] = df['feature_name'].apply(
        lambda x: get_outcome(x).get('metric', 'No verified data') if get_outcome(x) else 'No verified data'
    )
    df['feature_type_calc'] = df['feature_name'].apply(get_feature_type)
    
    # Binary labels for statistical analysis
    df['is_success'] = df['known_outcome'].isin(['SUCCESS', 'MODERATE_SUCCESS']).astype(int)
    df['is_failure'] = df['known_outcome'].isin(['FAILURE', 'WEAK']).astype(int)
    
    # Simplified outcome label
    df['outcome_label'] = df['known_outcome'].map({
        'SUCCESS': 'success',
        'MODERATE_SUCCESS': 'success',
        'FAILURE': 'failure',
        'WEAK': 'failure',
        'UNKNOWN': 'unknown'
    })
    
    df.to_csv(csv_path, index=False)
    
    # Print summary
    success_count = df['is_success'].sum()
    failure_count = df['is_failure'].sum()
    unknown_count = (df['known_outcome'] == 'UNKNOWN').sum()
    
    tier1_success = len(df[df['known_outcome'] == 'SUCCESS'])
    tier2_success = len(df[df['known_outcome'] == 'MODERATE_SUCCESS'])
    
    print(f"✓ Updated {csv_path.relative_to(PROJECT_ROOT)}")
    print(f"\n✓ {success_count} successes (Tier 1: {tier1_success}, Tier 2: {tier2_success})")
    print(f"✗ {failure_count} failures")
    print(f"? {unknown_count} unknown (need research)\n")
    
    # Show successes
    if success_count > 0:
        print("Successes:")
        successes = df[df['is_success'] == 1][['feature_name', 'company', 'known_outcome', 'outcome_metric']].sort_values('known_outcome')
        for _, row in successes.iterrows():
            icon = "⭐" if row['known_outcome'] == 'SUCCESS' else "✓"
            print(f"  {icon} {row['feature_name']} ({row['company']})")
            print(f"     {row['outcome_metric']}")
        print()
    
    # Show failures
    if failure_count > 0:
        print("Failures:")
        failures = df[df['is_failure'] == 1][['feature_name', 'company', 'outcome_metric']]
        for _, row in failures.iterrows():
            print(f"  ✗ {row['feature_name']} ({row['company']})")
            print(f"     {row['outcome_metric']}")
        print()
    
    # Show unknowns
    if unknown_count > 0:
        print(f"Unknown ({unknown_count} features need research):")
        unknowns = df[df['known_outcome'] == 'UNKNOWN'][['feature_name', 'company']]
        for _, row in unknowns.iterrows():
            print(f"  ? {row['feature_name']} ({row['company']})")
    
    return df


if __name__ == "__main__":
    print("Applying known business outcomes to labeled features...\n")
    df = apply_outcomes_to_csv()
    
    print("\nNext steps:")
    print("  1. python src/analysis/statistical_analysis.py")
    print("  2. python scripts/generate_visualizations.py\n")
