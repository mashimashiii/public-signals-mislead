"""
Generate all visualizations for the analysis.
Creates interactive Plotly charts showing key findings.

Usage: python scripts/generate_visualizations.py
"""

import pandas as pd
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.visualization.charts import (
    create_decay_vs_outcome_scatter,
    create_divergence_comparison,
    create_decision_matrix_heatmap,
    create_success_rate_by_type,
    create_statistical_comparison
)


def main():
    """Generate all visualizations."""
    
    print("\nGENERATING VISUALIZATIONS\n")
    
    csv_path = PROJECT_ROOT / 'data' / 'validation' / 'labeled_features.csv'
    df = pd.read_csv(csv_path)
    
    print(f"📂 Loaded {len(df)} features")
    print(f"   ✓ {df['is_success'].sum()} successes, ✗ {df['is_failure'].sum()} failures\n")
    
    # Prepare data
    if 'outcome' not in df.columns:
        df['outcome'] = df['known_outcome'].map({
            'SUCCESS': 'SUCCESS',
            'MODERATE_SUCCESS': 'SUCCESS',
            'FAILURE': 'FAILURE',
            'WEAK': 'FAILURE',
            'UNKNOWN': 'UNCERTAIN'
        })
    
    if 'engagement_score' not in df.columns:
        df['engagement_score'] = df['total_mentions'] * 10
    
    if 'outcome_metric' not in df.columns:
        df['outcome_metric'] = 'N/A'
    
    if 'success_binary' not in df.columns:
        df['success_binary'] = df['is_success']
    
    output_dir = PROJECT_ROOT / 'results' / 'figures'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Decay vs outcome scatter
    print("1️⃣ Creating decay vs outcome scatter...")
    try:
        create_decay_vs_outcome_scatter(df, output_path=str(output_dir / 'decay_vs_outcome.html'))
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    # 2. Key examples comparison
    print("\n2️⃣ Creating divergence comparison...")
    key_examples = ['Password Sharing Crackdown', 'AI DJ', 'Ad-Supported Tier', 'Games', 'GroupWatch']
    available_examples = [f for f in key_examples if f in df['feature_name'].values]
    
    try:
        create_divergence_comparison(df, features_to_show=available_examples,
                                    output_path=str(output_dir / 'divergence_examples.html'))
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    # 3. Decision matrix
    print("\n3️⃣ Creating decision matrix...")
    try:
        create_decision_matrix_heatmap(output_path=str(output_dir / 'decision_matrix.html'))
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    # 4. Success by type
    print("\n4️⃣ Creating success rate by type...")
    try:
        create_success_rate_by_type(df, output_path=str(output_dir / 'success_by_type.html'))
    except Exception as e:
        print(f"   ✗ Error: {e}")
    
    # 5. Statistical comparison
    print("\n5️⃣ Creating statistical comparison...")
    successes = df[df['is_success'] == 1]
    failures = df[df['is_failure'] == 1]
    
    if len(successes) > 0 and len(failures) > 0:
        success_metrics = {
            'decay_mean': successes['search_decay'].mean(),
            'mentions_mean': successes['total_mentions'].mean(),
            'negative_mean': successes['negative_ratio'].mean()
        }
        failure_metrics = {
            'decay_mean': failures['search_decay'].mean(),
            'mentions_mean': failures['total_mentions'].mean(),
            'negative_mean': failures['negative_ratio'].mean()
        }
        
        try:
            create_statistical_comparison(success_metrics, failure_metrics,
                                         output_path=str(output_dir / 'statistical_comparison.html'))
        except Exception as e:
            print(f"   ✗ Error: {e}")
    
    print("\n✓ VISUALIZATIONS COMPLETE")
    print(f"\n📁 Saved to: {output_dir.relative_to(PROJECT_ROOT)}")
    print("\nCreated files:")
    for file in output_dir.glob('*.html'):
        print(f"   • {file.name}")
    
    print("\n💡 Open HTML files in browser to view interactive charts")


if __name__ == "__main__":
    main()
