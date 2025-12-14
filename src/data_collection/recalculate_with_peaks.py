"""
Recalculate feature stickiness metrics using PEAK dates instead of launch dates.

Key insight: Features don't peak on launch day. Users discover features when they
have a reason to care (marketing push, key event, word of mouth).

This script:
1. Finds actual peak interest date for each feature
2. Calculates decay from peak (not from launch)
3. Provides accurate stickiness classifications

Usage: python src/data_collection/recalculate_with_peaks.py --input data/trends/MERGED_trends_data.csv
"""

import pandas as pd
import argparse
from datetime import timedelta
from pathlib import Path
from typing import Dict, Tuple


def find_peak_date(trends_df: pd.DataFrame, feature_name: str) -> Tuple[pd.Timestamp, float]:
    """Find date and value of maximum interest for a feature."""
    feature_data = trends_df[trends_df['feature_name'] == feature_name].copy()
    
    if feature_data.empty:
        return None, None
    
    peak_row = feature_data.loc[feature_data['interest'].idxmax()]
    return peak_row['date'], peak_row['interest']


def calculate_peak_based_decay(trends_df: pd.DataFrame, feature_name: str,
                               launch_date: pd.Timestamp, peak_date: pd.Timestamp,
                               peak_interest: float) -> Dict[str, float]:
    """
    Calculate decay metrics from PEAK date (not launch date).
    Returns dict with decay metrics and classification.
    """
    feature_data = trends_df[trends_df['feature_name'] == feature_name].copy()
    feature_data['date'] = pd.to_datetime(feature_data['date'])
    
    days_to_peak = (peak_date - launch_date).days
    
    # Week 4: 21-28 days AFTER peak
    week_4_data = feature_data[
        (feature_data['date'] >= peak_date + timedelta(days=21)) & 
        (feature_data['date'] < peak_date + timedelta(days=28))
    ]
    
    # Week 8: 56-63 days AFTER peak
    week_8_data = feature_data[
        (feature_data['date'] >= peak_date + timedelta(days=56)) & 
        (feature_data['date'] < peak_date + timedelta(days=63))
    ]
    
    # Calculate metrics
    if not week_4_data.empty:
        week_4_interest = week_4_data['interest'].mean()
        decay_rate_w4 = (peak_interest - week_4_interest) / peak_interest if peak_interest > 0 else None
    else:
        week_4_interest = None
        decay_rate_w4 = None
    
    if not week_8_data.empty:
        week_8_interest = week_8_data['interest'].mean()
        decay_rate_w8 = (peak_interest - week_8_interest) / peak_interest if peak_interest > 0 else None
    else:
        week_8_interest = None
        decay_rate_w8 = None
    
    # Classify based on Week 4 decay
    if decay_rate_w4 is None or decay_rate_w4 < 0:
        classification = 'unknown'
    elif decay_rate_w4 < 0.30:
        classification = 'sticky'
    elif decay_rate_w4 < 0.70:
        classification = 'mixed'
    else:
        classification = 'novelty'
    
    return {
        'days_to_peak': days_to_peak,
        'peak_interest': peak_interest,
        'week_4_interest': week_4_interest,
        'week_8_interest': week_8_interest,
        'decay_rate_w4': decay_rate_w4,
        'decay_rate_w8': decay_rate_w8,
        'classification': classification
    }


def recalculate_all_metrics(trends_df: pd.DataFrame) -> pd.DataFrame:
    """Recalculate metrics for all features using peak-based methodology."""
    trends_df['date'] = pd.to_datetime(trends_df['date'])
    trends_df['launch_date'] = pd.to_datetime(trends_df['launch_date'])
    
    results = []
    
    for feature_name in trends_df['feature_name'].unique():
        feature_data = trends_df[trends_df['feature_name'] == feature_name].iloc[0]
        
        peak_date, peak_interest = find_peak_date(trends_df, feature_name)
        
        if peak_date is None:
            continue
        
        metrics = calculate_peak_based_decay(
            trends_df, feature_name, feature_data['launch_date'], peak_date, peak_interest
        )
        
        result = {
            'feature_id': feature_data['feature_id'],
            'feature_name': feature_name,
            'company': feature_data['company'] if 'company' in feature_data else 'Unknown',
            'feature_type': feature_data['feature_type'] if 'feature_type' in feature_data else 'Unknown',
            'launch_date': feature_data['launch_date'],
            'peak_date': peak_date,
            **metrics
        }
        
        results.append(result)
    
    results_df = pd.DataFrame(results)
    return results_df.sort_values('decay_rate_w4')


def print_analysis(metrics_df: pd.DataFrame):
    """Print analysis of recalculated metrics."""
    print("\nRECALCULATED METRICS - Peak-Based Methodology\n")
    
    print(f"{'Feature':<35} {'Days to Peak':<15} {'W4 Decay':<12} {'W8 Decay':<12} {'Class':<10}")
    print("-"*100)
    
    for _, row in metrics_df.iterrows():
        decay_w4 = f"{row['decay_rate_w4']:.1%}" if pd.notna(row['decay_rate_w4']) else "N/A"
        decay_w8 = f"{row['decay_rate_w8']:.1%}" if pd.notna(row['decay_rate_w8']) else "N/A"
        print(f"{row['feature_name']:<35} {row['days_to_peak']:<15} {decay_w4:<12} {decay_w8:<12} {row['classification']:<10}")
    
    print("\nClassification breakdown:")
    print(metrics_df['classification'].value_counts().to_string())
    
    print("\nKey statistics:")
    print(f"  Average days to peak: {metrics_df['days_to_peak'].mean():.1f}")
    print(f"  Median days to peak: {metrics_df['days_to_peak'].median():.1f}")
    print(f"  Average Week 4 decay: {metrics_df['decay_rate_w4'].mean():.1%}")
    print(f"  Average Week 8 decay: {metrics_df['decay_rate_w8'].mean():.1%}")
    
    # Awareness patterns
    immediate = metrics_df[metrics_df['days_to_peak'] <= 7]
    delayed = metrics_df[metrics_df['days_to_peak'] > 7]
    
    if not immediate.empty:
        print(f"\nImmediate awareness (peak within 1 week): {len(immediate)} features")
        print(f"  Average decay: {immediate['decay_rate_w4'].mean():.1%}")
        print(f"  Classification: {immediate['classification'].value_counts().to_dict()}")
    
    if not delayed.empty:
        print(f"\nDelayed awareness (peak >1 week later): {len(delayed)} features")
        print(f"  Average decay: {delayed['decay_rate_w4'].mean():.1%}")
        print(f"  Classification: {delayed['classification'].value_counts().to_dict()}")


def main():
    """Main execution."""
    parser = argparse.ArgumentParser(description='Recalculate metrics using peak dates')
    parser.add_argument('--input', type=str, required=True, help='Path to trends data CSV')
    parser.add_argument('--output', type=str, default=None,
                       help='Path for output CSV (default: input_PEAK_metrics.csv)')
    
    args = parser.parse_args()
    
    print(f"📂 Loading trends data from: {args.input}")
    trends_df = pd.read_csv(args.input)
    print(f"   Loaded {len(trends_df)} rows for {trends_df['feature_name'].nunique()} features")
    
    print("\n🔄 Recalculating metrics using peak dates...")
    metrics_df = recalculate_all_metrics(trends_df)
    
    print_analysis(metrics_df)
    
    # Save results
    if args.output:
        output_path = Path(args.output)
    else:
        input_path = Path(args.input)
        output_path = input_path.parent / f"{input_path.stem}_PEAK_metrics.csv"
    
    metrics_df.to_csv(output_path, index=False)
    print(f"\n✓ Saved to: {output_path}")


if __name__ == "__main__":
    main()
