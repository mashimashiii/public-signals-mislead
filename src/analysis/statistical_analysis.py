"""
Statistical Analysis Module

Tests whether search decay and other public signals predict feature success.
Key finding (expected): They don't. Success and failure show similar decay patterns.
"""

from pathlib import Path
from typing import Dict, Tuple

import numpy as np
import pandas as pd
from scipy import stats


def load_labeled_data(path: str = "data/validation/labeled_features.csv") -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Load labeled data and separate into success/failure groups.

    We support two label schemas:
      - is_success / is_failure (preferred, from create_labeled_dataset.py)
      - success_binary (legacy: 1=success, 0=failure)

    Returns:
        (successes_df, failures_df, full_df)
    """
    df = pd.read_csv(path)

    if "is_success" in df.columns:
        successes = df[df["is_success"] == 1].copy()
        if "is_failure" in df.columns:
            failures = df[df["is_failure"] == 1].copy()
        else:
            failures = df[df["outcome_label"] == "failure"].copy()
        label_col = "is_success"
    elif "success_binary" in df.columns:
        successes = df[df["success_binary"] == 1].copy()
        failures = df[df["success_binary"] == 0].copy()
        label_col = "success_binary"
    else:
        raise ValueError(
            "No success label column found. Expected 'is_success' or 'success_binary' "
            f"in columns {list(df.columns)}"
        )

    # Keep the label column name on the frame for later
    df["_success_label_col"] = label_col

    return successes, failures, df


def _ttest_groups(x: np.ndarray, y: np.ndarray) -> Tuple[float, float]:
    """Helper: robust t-test that returns (nan, nan) if any group is empty."""
    if len(x) == 0 or len(y) == 0:
        return np.nan, np.nan
    return stats.ttest_ind(x, y, equal_var=False)  # Welch t-test


def test_decay_difference(successes: pd.DataFrame, failures: pd.DataFrame) -> Dict:
    """
    Test if successful features have different search decay than failures.
    """
    success_decay = successes["search_decay"].values
    failure_decay = failures["search_decay"].values

    t_stat, p_value = _ttest_groups(success_decay, failure_decay)

    success_mean = float(np.nanmean(success_decay)) if len(success_decay) else np.nan
    failure_mean = float(np.nanmean(failure_decay)) if len(failure_decay) else np.nan
    success_std = float(np.nanstd(success_decay, ddof=1)) if len(success_decay) > 1 else np.nan
    failure_std = float(np.nanstd(failure_decay, ddof=1)) if len(failure_decay) > 1 else np.nan

    # Effect size (Cohen's d)
    if np.isnan(success_std) or np.isnan(failure_std):
        cohens_d = np.nan
    else:
        pooled_std = np.sqrt((success_std**2 + failure_std**2) / 2)
        cohens_d = (success_mean - failure_mean) / pooled_std if pooled_std > 0 else np.nan

    significant = bool(p_value < 0.05) if not np.isnan(p_value) else False

    return {
        "metric": "search_decay",
        "success_mean": success_mean,
        "success_std": success_std,
        "failure_mean": failure_mean,
        "failure_std": failure_std,
        "t_statistic": t_stat,
        "p_value": p_value,
        "cohens_d": cohens_d,
        "significant": significant,
        "conclusion": "DOES NOT" if (not significant) else "DOES",
        "effect_size_label": interpret_effect_size(abs(cohens_d)) if not np.isnan(cohens_d) else "undefined",
    }


def test_mentions_difference(successes: pd.DataFrame, failures: pd.DataFrame) -> Dict:
    """
    Test if successful features have different Reddit engagement (total mentions).
    """
    success_mentions = successes["total_mentions"].values
    failure_mentions = failures["total_mentions"].values

    t_stat, p_value = _ttest_groups(success_mentions, failure_mentions)

    success_mean = float(np.nanmean(success_mentions)) if len(success_mentions) else np.nan
    failure_mean = float(np.nanmean(failure_mentions)) if len(failure_mentions) else np.nan
    success_std = float(np.nanstd(success_mentions, ddof=1)) if len(success_mentions) > 1 else np.nan
    failure_std = float(np.nanstd(failure_mentions, ddof=1)) if len(failure_mentions) > 1 else np.nan

    if np.isnan(success_std) or np.isnan(failure_std):
        cohens_d = np.nan
    else:
        pooled_std = np.sqrt((success_std**2 + failure_std**2) / 2)
        cohens_d = (success_mean - failure_mean) / pooled_std if pooled_std > 0 else np.nan

    significant = bool(p_value < 0.05) if not np.isnan(p_value) else False

    return {
        "metric": "total_mentions",
        "success_mean": success_mean,
        "success_std": success_std,
        "failure_mean": failure_mean,
        "failure_std": failure_std,
        "t_statistic": t_stat,
        "p_value": p_value,
        "cohens_d": cohens_d,
        "significant": significant,
        "conclusion": "DOES" if significant else "DOES NOT",
        "effect_size_label": interpret_effect_size(abs(cohens_d)) if not np.isnan(cohens_d) else "undefined",
    }


def test_sentiment_difference(successes: pd.DataFrame, failures: pd.DataFrame) -> Dict:
    """
    Test if successful features have different negative sentiment.
    """
    success_negative = successes["negative_ratio"].values
    failure_negative = failures["negative_ratio"].values

    t_stat, p_value = _ttest_groups(success_negative, failure_negative)

    success_mean = float(np.nanmean(success_negative)) if len(success_negative) else np.nan
    failure_mean = float(np.nanmean(failure_negative)) if len(failure_negative) else np.nan
    success_std = float(np.nanstd(success_negative, ddof=1)) if len(success_negative) > 1 else np.nan
    failure_std = float(np.nanstd(failure_negative, ddof=1)) if len(failure_negative) > 1 else np.nan

    significant = bool(p_value < 0.05) if not np.isnan(p_value) else False

    return {
        "metric": "negative_ratio",
        "success_mean": success_mean,
        "success_std": success_std,
        "failure_mean": failure_mean,
        "failure_std": failure_std,
        "t_statistic": t_stat,
        "p_value": p_value,
        "significant": significant,
        "conclusion": "DOES" if significant else "DOES NOT",
    }


def calculate_correlations(df: pd.DataFrame) -> pd.Series:
    """
    Calculate correlation of each feature with success.

    Uses whichever success label column exists.
    """
    candidate_cols = [
        "search_decay",
        "total_mentions",
        "negative_ratio",
        "positive_ratio",
        "neutral_ratio",
        "avg_score",
    ]
    feature_cols = [c for c in candidate_cols if c in df.columns]

    if not feature_cols:
        return pd.Series(dtype=float)

    label_col = df["_success_label_col"].iloc[0]

    corr = df[feature_cols + [label_col]].corr()[label_col].drop(label_col)
    return corr.sort_values(key=lambda x: x.abs(), ascending=False)


def find_high_decay_successes(successes: pd.DataFrame, threshold: float = 0.80) -> pd.DataFrame:
    """
    Find successful features with high search decay.
    """
    if "search_decay" not in successes.columns:
        return successes.iloc[0:0].copy()
    return successes[successes["search_decay"] > threshold].copy()


def interpret_effect_size(cohens_d: float) -> str:
    """Interpret Cohen's d effect size."""
    if np.isnan(cohens_d):
        return "undefined"
    if abs(cohens_d) < 0.2:
        return "negligible"
    elif abs(cohens_d) < 0.5:
        return "small"
    elif abs(cohens_d) < 0.8:
        return "medium"
    else:
        return "large"


def interpret_correlation(corr: float) -> str:
    """Interpret correlation strength."""
    if abs(corr) > 0.5:
        return "strong"
    elif abs(corr) > 0.3:
        return "moderate"
    else:
        return "weak"


def run_all_tests(labeled_path: str = "data/validation/labeled_features.csv") -> Dict:
    """
    Run complete statistical analysis.
    """
    successes, failures, df = load_labeled_data(labeled_path)

    decay_test = test_decay_difference(successes, failures)
    mentions_test = test_mentions_difference(successes, failures)
    sentiment_test = test_sentiment_difference(successes, failures)

    correlations = calculate_correlations(df)

    high_decay_successes = find_high_decay_successes(successes)

    return {
        "sample_sizes": {
            "successes": len(successes),
            "failures": len(failures),
            "total": len(df),
        },
        "decay_test": decay_test,
        "mentions_test": mentions_test,
        "sentiment_test": sentiment_test,
        "correlations": correlations.to_dict(),
        "high_decay_successes": {
            "count": len(high_decay_successes),
            "pct_of_successes": len(high_decay_successes) / len(successes) if len(successes) > 0 else 0.0,
            "features": high_decay_successes["feature_name"].tolist() if len(high_decay_successes) else [],
        },
    }


def print_results(results: Dict) -> None:
    """
    Print statistical results in readable format.
    """
    print("=" * 80)
    print("📊 STATISTICAL ANALYSIS: Search Decay vs Success")
    print("=" * 80)

    print(f"\n✅ Successes: {results['sample_sizes']['successes']}")
    print(f"❌ Failures: {results['sample_sizes']['failures']}")

    decay = results["decay_test"]

    print("\n" + "=" * 80)
    print("🧪 TEST 1: Search Decay - Success vs Failure")
    print("=" * 80)

    if np.isnan(decay["success_mean"]) or np.isnan(decay["failure_mean"]):
        print("\n⚠️  Not enough data (no successes or no failures) to run this test meaningfully.")
    else:
        print(f"\n📉 Search Decay Statistics:")
        print(f"   Successes:  {decay['success_mean']:.1%} (±{decay['success_std']:.1%})")
        print(f"   Failures:   {decay['failure_mean']:.1%} (±{decay['failure_std']:.1%})")
        print(f"   Difference: {abs(decay['success_mean'] - decay['failure_mean']):.1%}")

        print(f"\n📊 Independent t-test:")
        print(f"   t-statistic: {decay['t_statistic']:.3f}")
        print(f"   p-value: {decay['p_value']:.4f}")

        if decay["significant"]:
            print(f"   ⚠️  RESULT: Significant difference (p={decay['p_value']:.4f} < 0.05)")
        else:
            print(f"   ✅ RESULT: No significant difference (p={decay['p_value']:.4f} ≥ 0.05)")
            print(f"   📌 CONCLUSION: Search decay {decay['conclusion']} distinguish success from failure")

        print(f"\n📏 Effect size (Cohen's d): {decay['cohens_d']:.3f} ({decay['effect_size_label']})")

    # Mentions
    print("\n" + "=" * 80)
    print("🧪 TEST 2: Reddit Mentions - Success vs Failure")
    print("=" * 80)
    mentions = results["mentions_test"]
    print(f"\n💬 Reddit Mentions Statistics:")
    print(f"   Successes:  {mentions['success_mean']:.1f}")
    print(f"   Failures:   {mentions['failure_mean']:.1f}")
    print(f"\n📊 Independent t-test:")
    print(f"   p-value: {mentions['p_value']:.4f}")
    print(f"   📌 CONCLUSION: Engagement volume {mentions['conclusion']} distinguish success from failure")

    # Sentiment
    print("\n" + "=" * 80)
    print("🧪 TEST 3: Negative Sentiment - Success vs Failure")
    print("=" * 80)
    sentiment = results["sentiment_test"]
    print(f"\n😡 Negative Sentiment:")
    print(f"   Successes:  {sentiment['success_mean']:.1%}")
    print(f"   Failures:   {sentiment['failure_mean']:.1%}")
    print(f"   p-value: {sentiment['p_value']:.4f}")
    print(f"   📌 CONCLUSION: Negative sentiment {sentiment['conclusion']} distinguish success from failure")

    high_decay = results["high_decay_successes"]
    print("\n" + "=" * 80)
    print("🔥 KEY FINDING: Successes with High Decay")
    print("=" * 80)
    print(f"\n✅ Successes with >80% decay: {high_decay['count']} ({high_decay['pct_of_successes']:.0%})")
    if high_decay["features"]:
        print("\nFeatures:")
        for feature in high_decay["features"]:
            print(f"   • {feature}")
    else:
        print("   (no successful features above threshold / or no successes at all)")

    print("\n" + "=" * 80)
    print("📈 CORRELATION ANALYSIS")
    print("=" * 80)
    if results["correlations"]:
        print(f"\nCorrelation with success:")
        for feature, corr in results["correlations"].items():
            direction = "↑" if corr > 0 else "↓"
            strength = interpret_correlation(abs(corr))
            print(f"   {direction} {feature:20s}: {corr:+.3f} ({strength})")
    else:
        print("No numeric feature columns available for correlation analysis.")

    print("\n" + "=" * 80)
    print("🎯 SUMMARY OF FINDINGS")
    print("=" * 80)
    print(
        "\n(Interpretation depends on having at least a few successful features. "
        "Right now your labeled set has "
        f"{results['sample_sizes']['successes']} successes and "
        f"{results['sample_sizes']['failures']} failures.)"
    )


def save_results(results: Dict, output_path: str = "data/validation/statistical_results.csv") -> None:
    """
    Save core test results to CSV.
    """
    df = pd.DataFrame(
        [
            {
                "metric": results["decay_test"]["metric"],
                "success_mean": results["decay_test"]["success_mean"],
                "failure_mean": results["decay_test"]["failure_mean"],
                "p_value": results["decay_test"]["p_value"],
                "significant": results["decay_test"]["significant"],
            },
            {
                "metric": results["mentions_test"]["metric"],
                "success_mean": results["mentions_test"]["success_mean"],
                "failure_mean": results["mentions_test"]["failure_mean"],
                "p_value": results["mentions_test"]["p_value"],
                "significant": results["mentions_test"]["significant"],
            },
            {
                "metric": results["sentiment_test"]["metric"],
                "success_mean": results["sentiment_test"]["success_mean"],
                "failure_mean": results["sentiment_test"]["failure_mean"],
                "p_value": results["sentiment_test"]["p_value"],
                "significant": results["sentiment_test"]["significant"],
            },
        ]
    )

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"\n✅ Saved results to: {output_path}")


if __name__ == "__main__":
    results = run_all_tests()
    print_results(results)
    save_results(results)
