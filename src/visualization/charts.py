"""
Visualization module - creates interactive Plotly charts for analysis.
All charts use consistent styling for publication and LinkedIn posts.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path


# Consistent color scheme
COLORS = {
    'SUCCESS': '#00CC66',
    'MODERATE_SUCCESS': '#FFB84D',
    'FAILURE': '#FF4444',
    'WEAK': '#FF4444',
    'primary': '#2C3E50',
    'secondary': '#95A5A6',
    'background': 'rgba(240,240,240,0.5)'
}


def create_decay_vs_outcome_scatter(df: pd.DataFrame, output_path: str = 'results/figures/decay_vs_outcome.html') -> None:
    """
    Main finding visualization: success and failure show similar decay.
    Scatter plot with search decay vs Reddit mentions.
    """
    fig = px.scatter(
        df, x='search_decay', y='total_mentions', color='outcome', size='engagement_score',
        hover_data=['feature_name', 'outcome_metric'],
        title='The Paradox: Success and Failure Show Similar Search Decay',
        labels={
            'search_decay': 'Search Decay (4 weeks post-peak)',
            'total_mentions': 'Reddit Mentions',
            'outcome': 'Business Outcome'
        },
        color_discrete_map=COLORS,
        width=1000, height=700
    )
    
    # Add key finding annotation
    success_high_decay = len(df[(df['outcome'] == 'SUCCESS') & (df['search_decay'] > 0.80)])
    total_success = len(df[df['outcome'] == 'SUCCESS'])
    pct = (success_high_decay / total_success * 100) if total_success > 0 else 0
    
    fig.add_annotation(
        x=0.95, y=df['total_mentions'].max() * 0.8,
        text=f"{pct:.0f}% of successes show >80% decay<br>High decay ≠ Failure",
        showarrow=True, arrowhead=2, arrowsize=1, arrowwidth=2,
        arrowcolor=COLORS['SUCCESS'],
        font=dict(size=14, color=COLORS['SUCCESS']),
        bgcolor="white", bordercolor=COLORS['SUCCESS'], borderwidth=2
    )
    
    fig.update_layout(
        font=dict(size=14),
        title_font=dict(size=20, color=COLORS['primary']),
        plot_bgcolor=COLORS['background']
    )
    
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(output_path)
    print(f"   ✓ Saved: {output_path}")


def create_divergence_comparison(df: pd.DataFrame, features_to_show: list, 
                                 output_path: str = 'results/figures/divergence_examples.html') -> None:
    """
    Grouped bar chart comparing signals vs outcomes for key examples.
    Shows when public signals mislead (e.g., Netflix Password Sharing vs Disney+ GroupWatch).
    """
    examples = df[df['feature_name'].isin(features_to_show)].copy()
    
    fig = go.Figure()
    
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
        legend=dict(orientation='v', yanchor='top', y=0.99, xanchor='right', x=0.99)
    )
    
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(output_path)
    print(f"   ✓ Saved: {output_path}")


def create_decision_matrix_heatmap(output_path: str = 'results/figures/decision_matrix.html') -> None:
    """
    Heatmap showing decision recommendations based on decay + sentiment signals.
    Framework for interpreting external signals in product decisions.
    """
    decay_levels = ['Low (<50%)', 'Medium (50-80%)', 'High (>80%)']
    sentiments = ['Negative', 'Mixed', 'Positive']
    
    recommendations = [
        ['INVESTIGATE', 'UNCERTAIN', 'LIKELY SUCCESS'],
        ['UNCERTAIN', 'MONITOR', 'MONITOR'],
        ['INVESTIGATE', 'MONITOR', 'LIKELY SUCCESS']
    ]
    
    z_values = [[1, 2, 3], [2, 2, 2], [1, 2, 3]]
    
    fig = go.Figure(data=go.Heatmap(
        z=z_values, x=decay_levels, y=sentiments,
        text=recommendations, texttemplate='%{text}', textfont={"size": 14},
        colorscale=[[0, '#FF4444'], [0.5, '#FFB84D'], [1, '#00CC66']],
        showscale=False, hoverongaps=False
    ))
    
    fig.update_layout(
        title='Decision Matrix: How to Interpret External Signals',
        title_font=dict(size=20, color=COLORS['primary']),
        xaxis_title='Search Decay', yaxis_title='Reddit Sentiment',
        font=dict(size=14), height=500, width=800
    )
    
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(output_path)
    print(f"   ✓ Saved: {output_path}")


def create_success_rate_by_type(df: pd.DataFrame, output_path: str = 'results/figures/success_by_type.html') -> None:
    """Bar chart showing success rate by feature type (monetization, AI, content, etc)."""
    type_analysis = df.groupby('feature_type').agg({
        'success_binary': ['count', 'sum', 'mean']
    }).reset_index()
    
    type_analysis.columns = ['feature_type', 'total', 'successes', 'success_rate']
    type_analysis = type_analysis[type_analysis['total'] >= 2].sort_values('success_rate', ascending=False)
    
    fig = px.bar(
        type_analysis, x='feature_type', y='success_rate',
        title='Success Rate by Feature Type',
        labels={'success_rate': 'Success Rate', 'feature_type': 'Feature Type'},
        text='success_rate', color='success_rate',
        color_continuous_scale='RdYlGn', range_color=[0, 1]
    )
    
    fig.update_traces(texttemplate='%{text:.0%}', textposition='outside')
    fig.update_layout(
        font=dict(size=14),
        title_font=dict(size=20, color=COLORS['primary']),
        showlegend=False, height=600, yaxis_tickformat='.0%'
    )
    
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(output_path)
    print(f"   ✓ Saved: {output_path}")


def create_statistical_comparison(success_metrics: dict, failure_metrics: dict,
                                  output_path: str = 'results/figures/statistical_comparison.html') -> None:
    """Side-by-side comparison of success vs failure metrics."""
    metrics = ['Search Decay', 'Reddit Mentions', 'Negative Sentiment']
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        name='Successes', x=metrics,
        y=[success_metrics['decay_mean'], success_metrics['mentions_mean'], success_metrics['negative_mean']],
        marker_color=COLORS['SUCCESS'],
        text=[f"{success_metrics['decay_mean']:.1%}", f"{success_metrics['mentions_mean']:.1f}", 
              f"{success_metrics['negative_mean']:.1%}"],
        textposition='outside'
    ))
    
    fig.add_trace(go.Bar(
        name='Failures', x=metrics,
        y=[failure_metrics['decay_mean'], failure_metrics['mentions_mean'], failure_metrics['negative_mean']],
        marker_color=COLORS['FAILURE'],
        text=[f"{failure_metrics['decay_mean']:.1%}", f"{failure_metrics['mentions_mean']:.1f}",
              f"{failure_metrics['negative_mean']:.1%}"],
        textposition='outside'
    ))
    
    fig.update_layout(
        title='Success vs Failure: Metric Comparison',
        barmode='group', height=600,
        font=dict(size=14),
        title_font=dict(size=20, color=COLORS['primary']),
        yaxis_title='Value', showlegend=True
    )
    
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(output_path)
    print(f"   ✓ Saved: {output_path}")
