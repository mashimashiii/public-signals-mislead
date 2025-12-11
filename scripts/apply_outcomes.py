"""
Apply known business outcomes to labeled features CSV.

This is a utility script that runs once to populate the labeled_features.csv
with verified business outcomes from config/outcomes.py.

Usage (from project root):
    python scripts/apply_outcomes.py
"""

import pandas as pd
from pathlib import Path
import sys

# Add project root to Python path for imports
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from config.outcomes import KNOWN_OUTCOMES, get_outcome, get_feature_type


def apply_outcomes_to_csv():
    """
    Apply known business outcomes from config to the labeled features CSV.
    
    Updates columns:
        - known_outcome: SUCCESS/MODERATE_SUCCESS/FAILURE/WEAK/UNKNOWN
        - outcome_metric: Verified business metric
        - feature_type_calc: Feature type from config
        - is_success: Binary (1 for success/moderate success, 0 otherwise)
        - is_failure: Binary (1 for failure/weak, 0 otherwise)
        - outcome_label: Simplified label for analysis
    """
    
    # Load current CSV
    csv_path = PROJECT_ROOT / 'data' / 'validation' / 'labeled_features.csv'
    df = pd.read_csv(csv_path)
    
    print(f"📂 Loaded {len(df)} features from {csv_path.relative_to(PROJECT_ROOT)}")
    print(f"   Companies: {', '.join(df['company'].unique())}")
    
    # Apply outcomes from config
    def get_outcome_label(feature_name):
        outcome = get_outcome(feature_name)
        if not outcome:
            return 'UNKNOWN'
        return outcome.get('outcome', 'UNKNOWN')
    
    def get_outcome_metric(feature_name):
        outcome = get_outcome(feature_name)
        if not outcome:
            return 'No verified data'
        return outcome.get('metric', 'No metric')
    
    # Update columns
    df['known_outcome'] = df['feature_name'].apply(get_outcome_label)
    df['outcome_metric'] = df['feature_name'].apply(get_outcome_metric)
    df['feature_type_calc'] = df['feature_name'].apply(get_feature_type)
    
    # Create binary labels for statistical analysis
    df['is_success'] = df['known_outcome'].isin(['SUCCESS', 'MODERATE_SUCCESS']).astype(int)
    df['is_failure'] = df['known_outcome'].isin(['FAILURE', 'WEAK']).astype(int)
    
    # Update outcome_label to simplified format
    df['outcome_label'] = df['known_outcome'].map({
        'SUCCESS': 'success',
        'MODERATE_SUCCESS': 'success',
        'FAILURE': 'failure',
        'WEAK': 'failure',
        'UNKNOWN': 'unknown'
    })
    
    # Save updated CSV
    df.to_csv(csv_path, index=False)
    
    print(f"\n✅ Updated {csv_path.relative_to(PROJECT_ROOT)}")
    
    # Print detailed summary
    print("\n" + "="*80)
    print("📊 OUTCOME SUMMARY")
    print("="*80)
    
    success_count = df['is_success'].sum()
    failure_count = df['is_failure'].sum()
    unknown_count = (df['known_outcome'] == 'UNKNOWN').sum()
    
    print(f"\n✅ Successes: {success_count}")
    tier1_success = len(df[(df['known_outcome'] == 'SUCCESS')])
    tier2_success = len(df[(df['known_outcome'] == 'MODERATE_SUCCESS')])
    print(f"   - Strong (Tier 1): {tier1_success}")
    print(f"   - Moderate (Tier 2): {tier2_success}")
    
    print(f"\n❌ Failures: {failure_count}")
    
    print(f"\n❓ Unknown: {unknown_count}")
    print(f"   (Need research to classify)")
    
    # Show successes
    print("\n" + "="*80)
    print("SUCCESS FEATURES:")
    print("="*80)
    successes = df[df['is_success'] == 1][['feature_name', 'company', 'known_outcome', 'outcome_metric']].sort_values('known_outcome')
    for _, row in successes.iterrows():
        icon = "🌟" if row['known_outcome'] == 'SUCCESS' else "✅"
        print(f"\n{icon} {row['feature_name']} ({row['company']})")
        print(f"   📊 {row['outcome_metric']}")
    
    # Show failures
    print("\n" + "="*80)
    print("FAILURE FEATURES:")
    print("="*80)
    failures = df[df['is_failure'] == 1][['feature_name', 'company', 'outcome_metric']]
    for _, row in failures.iterrows():
        print(f"\n❌ {row['feature_name']} ({row['company']})")
        print(f"   📊 {row['outcome_metric']}")
    
    # Show unknowns
    if unknown_count > 0:
        print("\n" + "="*80)
        print("UNKNOWN FEATURES (Need Research):")
        print("="*80)
        unknowns = df[df['known_outcome'] == 'UNKNOWN'][['feature_name', 'company']]
        for _, row in unknowns.iterrows():
            print(f"   ❓ {row['feature_name']} ({row['company']})")
    
    return df


if __name__ == "__main__":
    print("🔧 Applying known business outcomes to labeled features...")
    print("")
    
    df = apply_outcomes_to_csv()
    
    print("\n" + "="*80)
    print("🎉 DONE!")
    print("="*80)
    print("\nNext steps:")
    print("   1. python src/analysis/statistical_analysis.py")
    print("   2. python scripts/generate_visualizations.py")
    print("")