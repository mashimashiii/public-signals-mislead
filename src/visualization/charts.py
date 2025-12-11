"""
Visualization Module

Creates publication-quality interactive charts for analysis and LinkedIn.
All visualizations use Plotly for consistency and interactivity.

"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
from typing import Optional


# Consistent color scheme across all visualizations
COLORS = {
    'SUCCESS': '#00CC66',           # Green
    'MODERATE_SUCCESS': '#FFB84D',  # Orange
    'FAILURE': '#FF4444',           # Red
    'WEAK': '#FF4444',              # Red
    'primary': '#2C3E50',           # Dark blue-gray for text
    'secondary': '#95A5A6',         # Light gray for secondary elements
    'background': 'rgba(240,240,240,0.5)'
}


def create_decay_vs_outcome_scatter(
    df: pd.DataFrame,
    output_path: str = 'results/figures/decay_vs_outcome.html'
) -> None:
    """
    Create scatter plot showing search decay vs business outcome.
    
    This is the KEY FINDING visualization: success and failure show similar decay.
    
    Args:
        df: DataFrame with labeled features (must have: search_decay, total_mentions,
            outcome, engagement_score, feature_name, outcome_metric)
        output_path: Where to save the HTML file
    """
    fig = px.scatter(
        df,
        x='search_decay',
        y='total_mentions',
        color='outcome',
        size='engagement_score',
        hover_data=['feature_name', 'outcome_metric'],
        title='The Paradox: Success and Failure Show Similar Search Decay',
        labels={
            'search_decay': 'Search Decay (4 weeks post-peak)',
            'total_mentions': 'Reddit Mentions',
            'outcome': 'Business Outcome'
        },
        color_discrete_map=COLORS,
        width=1000,
        height=700
    )
    
    # Add key insight annotation
    success_high_decay = len(df[(df['outcome'] == 'SUCCESS') & (df['search_decay'] > 0.80)])
    total_success = len(df[df['outcome'] == 'SUCCESS'])
    pct = (success_high_decay / total_success * 100) if total_success > 0 else 0
    
    fig.add_annotation(
        x=0.95, y=df['total_mentions'].max() * 0.8,
        text=f"{pct:.0f}% of successes show >80% decay<br>High decay ≠ Failure",
        showarrow=True,
        arrowhead=2,
        arrowsize=1,
        arrowwidth=2,
        arrowcolor=COLORS['SUCCESS'],
        font=dict(size=14, color=COLORS['SUCCESS']),
        bgcolor="white",
        bordercolor=COLORS['SUCCESS'],
        borderwidth=2
    )
    
    fig.update_layout(
        font=dict(size=14),
        title_font=dict(size=20, color=COLORS['primary']),
        plot_bgcolor=COLORS['background']
    )
    
    # Save
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(output_path)
    print(f"   ✅ Saved: {output_path}")


def create_feature_importance_chart(
    importance_df: pd.DataFrame,
    output_path: str = 'results/figures/feature_importance.html'
) -> None:
    """
    Create horizontal bar chart showing feature importance from ML model.
    
    Args:
        importance_df: DataFrame with columns 'feature' and 'importance'
        output_path: Where to save the HTML file
    """
    # Sort for horizontal bar (lowest to highest reads top to bottom)
    df_sorted = importance_df.sort_values('importance', ascending=True)
    
    fig = px.bar(
        df_sorted,
        x='importance',
        y='feature',
        orientation='h',
        title='What Actually Predicts Success? (ML Feature Importance)',
        labels={'importance': 'Predictive Power', 'feature': ''},
        color='importance',
        color_continuous_scale='Viridis'
    )
    
    # Annotate the least important feature (search_decay)
    least_important = df_sorted.iloc[0]
    fig.add_annotation(
        x=least_important['importance'] + 0.02,
        y=0,
        text=f"{least_important['feature']}<br>is LEAST predictive",
        showarrow=True,
        arrowhead=2,
        font=dict(size=12, color='#E74C3C')
    )
    
    fig.update_layout(
        font=dict(size=14),
        title_font=dict(size=20, color=COLORS['primary']),
        showlegend=False,
        height=600
    )
    
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(output_path)
    print(f"   ✅ Saved: {output_path}")


def create_divergence_comparison(
    df: pd.DataFrame,
    features_to_show: list,
    output_path: str = 'results/figures/divergence_examples.html'
) -> None:
    """
    Create grouped bar chart comparing signals vs outcomes for key examples.
    
    Args:
        df: DataFrame with labeled features
        features_to_show: List of feature names to include in chart
        output_path: Where to save the HTML file
    """
    # Filter to selected features
    examples = df[df['feature_name'].isin(features_to_show)].copy()
    
    fig = go.Figure()
    
    # Add bar for each feature
    for idx, row in examples.iterrows():
        color = COLORS['SUCCESS'] if row['success_binary'] == 1 else COLORS['FAILURE']
        
        fig.add_trace(go.Bar(
            name=row['feature_name'],
            x=['Search Decay', 'Negative Sentiment'],
            y=[row['search_decay'] * 100, row['negative_ratio'] * 100],
            marker_color=color,
            text=[f"{row['search_decay']:.0%}", f"{row['negative_ratio']:.0%}"],
            textposition='outside',
            showlegend=True
        ))
    
    fig.update_layout(
        title='When Public Signals Mislead: Divergence Examples',
        yaxis_title='Percentage',
        barmode='group',
        height=600,
        font=dict(size=14),
        title_font=dict(size=20, color=COLORS['primary']),
        legend=dict(
            orientation='v',
            yanchor='top',
            y=0.99,
            xanchor='right',
            x=0.99
        )
    )
    
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(output_path)
    print(f"   ✅ Saved: {output_path}")


def create_decision_matrix_heatmap(
    output_path: str = 'results/figures/decision_matrix.html'
) -> None:
    """
    Create heatmap showing decision recommendations based on signals.
    
    Args:
        output_path: Where to save the HTML file
    """
    # Define decision logic
    decay_levels = ['Low (<50%)', 'Medium (50-80%)', 'High (>80%)']
    sentiments = ['Negative', 'Mixed', 'Positive']
    
    # Create recommendation matrix
    recommendations = [
        ['INVESTIGATE', 'UNCERTAIN', 'LIKELY SUCCESS'],      # Negative
        ['UNCERTAIN', 'MONITOR', 'MONITOR'],                 # Mixed
        ['INVESTIGATE', 'MONITOR', 'LIKELY SUCCESS']         # Positive
    ]
    
    # Create z-values for color (1=red, 2=yellow, 3=green)
    z_values = [
        [1, 2, 3],  # Negative
        [2, 2, 2],  # Mixed
        [1, 2, 3]   # Positive
    ]
    
    fig = go.Figure(data=go.Heatmap(
        z=z_values,
        x=decay_levels,
        y=sentiments,
        text=recommendations,
        texttemplate='%{text}',
        textfont={"size": 14},
        colorscale=[[0, '#FF4444'], [0.5, '#FFB84D'], [1, '#00CC66']],
        showscale=False,
        hoverongaps=False
    ))
    
    fig.update_layout(
        title='Decision Matrix: How to Interpret External Signals',
        title_font=dict(size=20, color=COLORS['primary']),
        xaxis_title='Search Decay',
        yaxis_title='Reddit Sentiment',
        font=dict(size=14),
        height=500,
        width=800
    )
    
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(output_path)
    print(f"   ✅ Saved: {output_path}")


def create_success_rate_by_type(
    df: pd.DataFrame,
    output_path: str = 'results/figures/success_by_type.html'
) -> None:
    """
    Create bar chart showing success rate by feature type.
    
    Args:
        df: DataFrame with labeled features (must have: feature_type, success_binary)
        output_path: Where to save the HTML file
    """
    # Group by feature type (only include types with 2+ features)
    type_analysis = df.groupby('feature_type').agg({
        'success_binary': ['count', 'sum', 'mean']
    }).reset_index()
    
    type_analysis.columns = ['feature_type', 'total', 'successes', 'success_rate']
    type_analysis = type_analysis[type_analysis['total'] >= 2]
    
    # Sort by success rate
    type_analysis = type_analysis.sort_values('success_rate', ascending=False)
    
    fig = px.bar(
        type_analysis,
        x='feature_type',
        y='success_rate',
        title='Success Rate by Feature Type',
        labels={'success_rate': 'Success Rate', 'feature_type': 'Feature Type'},
        text='success_rate',
        color='success_rate',
        color_continuous_scale='RdYlGn',
        range_color=[0, 1]
    )
    
    fig.update_traces(texttemplate='%{text:.0%}', textposition='outside')
    fig.update_layout(
        font=dict(size=14),
        title_font=dict(size=20, color=COLORS['primary']),
        showlegend=False,
        height=600,
        yaxis_tickformat='.0%'
    )
    
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(output_path)
    print(f"   ✅ Saved: {output_path}")


def create_statistical_comparison(
    success_metrics: dict,
    failure_metrics: dict,
    output_path: str = 'results/figures/statistical_comparison.html'
) -> None:
    """
    Create side-by-side comparison of success vs failure metrics.
    
    Args:
        success_metrics: Dict with keys 'decay_mean', 'mentions_mean', 'negative_mean'
        failure_metrics: Dict with keys 'decay_mean', 'mentions_mean', 'negative_mean'
        output_path: Where to save the HTML file
    """
    metrics = ['Search Decay', 'Reddit Mentions', 'Negative Sentiment']
    
    fig = go.Figure()
    
    # Success bars
    fig.add_trace(go.Bar(
        name='Successes',
        x=metrics,
        y=[
            success_metrics['decay_mean'],
            success_metrics['mentions_mean'],
            success_metrics['negative_mean']
        ],
        marker_color=COLORS['SUCCESS'],
        text=[
            f"{success_metrics['decay_mean']:.1%}",
            f"{success_metrics['mentions_mean']:.1f}",
            f"{success_metrics['negative_mean']:.1%}"
        ],
        textposition='outside'
    ))
    
    # Failure bars
    fig.add_trace(go.Bar(
        name='Failures',
        x=metrics,
        y=[
            failure_metrics['decay_mean'],
            failure_metrics['mentions_mean'],
            failure_metrics['negative_mean']
        ],
        marker_color=COLORS['FAILURE'],
        text=[
            f"{failure_metrics['decay_mean']:.1%}",
            f"{failure_metrics['mentions_mean']:.1f}",
            f"{failure_metrics['negative_mean']:.1%}"
        ],
        textposition='outside'
    ))
    
    fig.update_layout(
        title='Success vs Failure: Metric Comparison',
        barmode='group',
        height=600,
        font=dict(size=14),
        title_font=dict(size=20, color=COLORS['primary']),
        yaxis_title='Value',
        showlegend=True
    )
    
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(output_path)
    print(f"   ✅ Saved: {output_path}")


def generate_all_visualizations(labeled_df: pd.DataFrame) -> None:
    """
    Generate all visualizations for the project.
    
    Args:
        labeled_df: DataFrame with labeled features
    """
    print("\n" + "="*80)
    print("📊 CREATING VISUALIZATIONS")
    print("="*80)
    
    # 1. Main finding: Decay vs Outcome
    print("\n1. Search Decay vs Outcome scatter...")
    create_decay_vs_outcome_scatter(labeled_df)
    
    # 2. Feature importance (requires model results)
    print("\n2. Feature importance bar chart...")
    print("   ⏭️  Skipped: Run ML model first to get importance values")
    
    # 3. Divergence examples
    print("\n3. Divergence comparison...")
    key_examples = [
        'Password Sharing Crackdown',
        'AI DJ',
        'Ad-Supported Tier',
        'Games',
        'GroupWatch'
    ]
    create_divergence_comparison(labeled_df, key_examples)
    
    # 4. Decision matrix
    print("\n4. Decision matrix heatmap...")
    create_decision_matrix_heatmap()
    
    # 5. Success by type
    print("\n5. Success rate by feature type...")
    create_success_rate_by_type(labeled_df)
    
    # 6. Statistical comparison
    print("\n6. Statistical comparison...")
    successes = labeled_df[labeled_df['success_binary'] == 1]
    failures = labeled_df[labeled_df['success_binary'] == 0]
    
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
    
    create_statistical_comparison(success_metrics, failure_metrics)
    
    print("\n" + "="*80)
    print("✅ VISUALIZATIONS COMPLETE")
    print("="*80)
    print("\nCreated 5 visualizations:")
    print("   1. Search decay vs outcome (scatter)")
    print("   2. Divergence examples (grouped bar)")
    print("   3. Decision matrix (heatmap)")
    print("   4. Success by feature type (bar)")
    print("   5. Statistical comparison (grouped bar)")
    print("\nAll saved to: results/figures/")


if __name__ == "__main__":
    # Test with sample data
    print("⚠️  Run this from main analysis script, not standalone")
    print("   Usage: from visualization import generate_all_visualizations")