"""
Reddit sentiment validation for feature launches.

Combines Reddit mentions + sentiment analysis with Google Trends decay data to classify
feature adoption patterns. Core logic for distinguishing success from failure.

Classification:
- High decay + positive sentiment + high mentions = ADOPTION (learned, stopped searching)
- High decay + negative sentiment = ABANDONMENT (tried, gave up)
- Low decay + positive sentiment = SUSTAINED_INTEREST (rare)
- High decay + few mentions = LOW_AWARENESS (never gained traction)
- Missing decay = NO_DECAY_DATA (sentiment still reported)
- Everything else = UNCERTAIN (mixed signals)
"""

import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import Counter

import pandas as pd

from .reddit_config import (
    FEATURE_OVERRIDES, FEATURE_COMPANY_GUARDS, FEATURE_EXPANSIONS,
    MAX_KEYWORDS_PER_FEATURE, COMPANY_SUBREDDITS
)
from .reddit_clients import BaseRedditClient, PrawRedditClient, PublicRedditClient

try:
    import praw
except ImportError:
    praw = None


def infer_company_from_keyword(keyword: Optional[str]) -> Optional[str]:
    """
    Infer company name from keyword field in trends CSV.
    Returns canonical company name or None if not detected.
    
    Examples: 'Spotify AI DJ' -> 'Spotify', 'Netflix password sharing' -> 'Netflix'
    """
    if not isinstance(keyword, str):
        return None

    k = keyword.lower().strip()

    # Order matters - check specific patterns first to avoid false positives
    if "spotify" in k:
        return "Spotify"
    if "netflix" in k:
        return "Netflix"
    if "disney plus" in k or "disney+" in k:
        return "Disney+"
    if "youtube tv" in k:  # Must check before generic "youtube"
        return "YouTube TV"
    if "youtube" in k:
        return "YouTube Premium"
    if "apple music" in k:
        return "Apple Music"
    if "peloton" in k:
        return "Peloton"
    if "paramount plus" in k or "paramount" in k:
        return "Paramount+"
    if "hulu" in k:
        return "Hulu"
    if k.startswith("x ") or " x " in k or "grok ai" in k or "twitter" in k:
        return "Twitter/X"

    return None


def enforce_feature_company_guard(feature_name: str, company: str) -> bool:
    """
    Enforce guardrails for features that must belong to specific products.
    Prevents mixing data from YouTube TV with YouTube Premium, Disney+ with Hulu, etc.
    Returns False if guardrail violated (feature should be skipped).
    """
    allowed = FEATURE_COMPANY_GUARDS.get(feature_name)
    if not allowed:
        return True  # No guard defined

    if company in allowed:
        return True

    print(f"⚠ Guardrail: '{feature_name}' expected in {allowed}, got '{company}' - skipping to avoid cross-product mixing")
    return False


def is_twitter_premium_feature(feature_name: str) -> bool:
    """
    Check if feature is a Twitter/X premium tier (vs product feature).
    Returns True for pricing/tier features like "X Premium Blue".
    """
    name = feature_name.lower()
    premium_markers = ["premium", "blue", "x premium", "x blue", "subscription", "subscribers"]
    return any(marker in name for marker in premium_markers)


def generate_keywords(feature_name: str, company: str) -> List[str]:
    """
    Generate Reddit search keywords from feature name and company.
    
    Goals:
    - Keep API calls small (rate-limit friendly)
    - Capture main ways people discuss the feature
    - Avoid combinatorial explosion
    
    Strategy:
    - Base patterns (feature name, company + feature)
    - Token-level expansions (if tokens match FEATURE_EXPANSIONS)
    - Company-specific terms
    - Deduplicate and cap at MAX_KEYWORDS_PER_FEATURE (default 8)
    """
    keywords = set()
    
    # Base patterns
    keywords.add(feature_name.lower())
    keywords.add(f"{company.lower()} {feature_name.lower()}")

    # Token expansions
    feature_lower = feature_name.lower()
    for token, expansions in FEATURE_EXPANSIONS.items():
        if token in feature_lower or any(exp in feature_lower for exp in expansions):
            keywords.update(expansions[:3])  # Take first 3 expansions

    # Company-specific terms
    company_lower = company.lower()
    if "youtube" in company_lower:
        keywords.add("youtube premium" if "premium" in company_lower else "youtube tv")
    elif "spotify" in company_lower:
        keywords.add("spotify")
    elif "netflix" in company_lower:
        keywords.add("netflix")
    elif "disney" in company_lower:
        keywords.add("disney plus")
    elif "twitter" in company_lower or "x" == company_lower:
        if is_twitter_premium_feature(feature_name):
            keywords.update(["twitter blue", "x premium"])
        else:
            keywords.add("x")

    # Deduplicate and limit
    keywords = list(keywords)[:MAX_KEYWORDS_PER_FEATURE]
    return keywords


class RedditValidator:
    """
    Validates feature success using Reddit sentiment + Google Trends decay.
    Multi-signal validation framework for product analytics.
    """

    def __init__(self, use_praw: bool = True):
        """Initialize with PRAW (authenticated) or public JSON client."""
        self.subreddits = COMPANY_SUBREDDITS

        if use_praw and praw is not None:
            client_id = os.getenv("REDDIT_CLIENT_ID")
            client_secret = os.getenv("REDDIT_CLIENT_SECRET")
            username = os.getenv("REDDIT_USERNAME")
            password = os.getenv("REDDIT_PASSWORD")

            if all([client_id, client_secret, username, password]):
                reddit = praw.Reddit(
                    client_id=client_id,
                    client_secret=client_secret,
                    username=username,
                    password=password,
                    user_agent="feature-validator/1.0"
                )
                self.client = PrawRedditClient(reddit)
                print("✓ Using PRAW (authenticated Reddit API)")
            else:
                self.client = PublicRedditClient()
                print("⚠ Missing credentials - using public JSON (slower)")
        else:
            self.client = PublicRedditClient()
            print("Using public JSON client")

    def search_feature_mentions(self, feature_name: str, company: str, launch_date: str,
                               search_keywords: List[str]) -> List[Dict]:
        """
        Search Reddit for feature mentions across multiple keywords.
        Returns combined list of mentions from all keywords (deduplicated by URL).
        """
        subreddit = self.subreddits.get(company)
        if not subreddit:
            print(f"⚠ No subreddit mapped for {company}")
            return []

        # Time window: 30 days before to 90 days after launch
        launch = datetime.strptime(launch_date, "%Y-%m-%d")
        start_ts = int((launch - timedelta(days=30)).timestamp())
        end_ts = int((launch + timedelta(days=90)).timestamp())

        print(f"\nSearching r/{subreddit} for '{feature_name}'")
        print(f"  Keywords: {', '.join(search_keywords[:5])}" + 
              (f" +{len(search_keywords)-5} more" if len(search_keywords) > 5 else ""))

        all_mentions = []
        seen_urls = set()

        for keyword in search_keywords:
            mentions = self.client.search_mentions(
                subreddit=subreddit,
                keyword=keyword,
                start_ts=start_ts,
                end_ts=end_ts,
                comment_limit=10,
                max_posts=100
            )

            # Deduplicate by URL
            for mention in mentions:
                url = mention.get("url", "")
                if url not in seen_urls:
                    seen_urls.add(url)
                    all_mentions.append(mention)

        print(f"  Found {len(all_mentions)} unique mentions")
        return all_mentions

    def analyze_sentiment(self, mentions: List[Dict]) -> Dict:
        """
        Analyze sentiment from Reddit mentions using keyword matching.
        Returns dict with sentiment ratios, label, and mention stats.
        """
        if not mentions:
            return {
                "total_mentions": 0,
                "positive_ratio": 0.0,
                "negative_ratio": 0.0,
                "neutral_ratio": 0.0,
                "avg_score": 0.0,
                "sentiment_label": "no_data",
                "positive_count": 0,
                "negative_count": 0,
                "neutral_count": 0
            }

        positive_keywords = [
            "love", "great", "amazing", "perfect", "awesome", "excellent",
            "fantastic", "helpful", "useful", "impressed", "best", "favorite"
        ]

        negative_keywords = [
            "hate", "terrible", "awful", "worst", "horrible", "useless",
            "annoying", "frustrating", "disappointed", "regret", "waste",
            "broken", "bug", "issue", "problem", "cancel", "unsubscribe"
        ]

        sentiments: List[str] = []
        scores: List[float] = []

        for mention in mentions:
            text = f"{mention.get('title', '')} {mention.get('text', '')}".lower()

            positive_count = sum(1 for word in positive_keywords if word in text)
            negative_count = sum(1 for word in negative_keywords if word in text)

            if positive_count > negative_count:
                sentiments.append("positive")
            elif negative_count > positive_count:
                sentiments.append("negative")
            else:
                sentiments.append("neutral")

            scores.append(mention.get("score", 0))

        sentiment_counts = Counter(sentiments)
        total = len(sentiments)

        positive_ratio = sentiment_counts["positive"] / total
        negative_ratio = sentiment_counts["negative"] / total
        neutral_ratio = sentiment_counts["neutral"] / total

        # Overall label - requires >50% for positive/negative
        if positive_ratio > 0.5:
            sentiment_label = "positive"
        elif negative_ratio > 0.5:
            sentiment_label = "negative"
        else:
            sentiment_label = "mixed"

        return {
            "total_mentions": total,
            "positive_ratio": positive_ratio,
            "negative_ratio": negative_ratio,
            "neutral_ratio": neutral_ratio,
            "avg_score": sum(scores) / len(scores) if scores else 0.0,
            "sentiment_label": sentiment_label,
            "positive_count": sentiment_counts["positive"],
            "negative_count": sentiment_counts["negative"],
            "neutral_count": sentiment_counts["neutral"]
        }

    def classify_feature(self, search_decay: Optional[float], sentiment: Dict) -> Dict[str, str]:
        """
        Classify feature based on decay + sentiment signals.
        
        Multi-signal validation framework: search decay alone is ambiguous
        (could mean adoption OR abandonment). Sentiment breaks the tie.
        
        Rules:
        - High decay (>70%) + Positive + High mentions = ADOPTION (learned it)
        - High decay (>70%) + Negative = ABANDONMENT (gave up)
        - Low decay (<30%) + Positive = SUSTAINED_INTEREST (rare)
        - High decay + Few mentions (<10) = LOW_AWARENESS (no traction)
        - Missing decay = NO_DECAY_DATA (can't classify)
        - Else = UNCERTAIN (mixed signals)
        """
        if search_decay is None or pd.isna(search_decay):
            return {
                "classification": "NO_DECAY_DATA",
                "explanation": "Decay metrics not available - can't classify adoption vs abandonment. Sentiment reported."
            }

        high_decay = search_decay > 0.70
        low_decay = search_decay < 0.30
        positive = sentiment["sentiment_label"] == "positive"
        negative = sentiment["sentiment_label"] == "negative"
        high_mentions = sentiment["total_mentions"] > 20

        if high_decay and positive and high_mentions:
            return {
                "classification": "ADOPTION",
                "explanation": "High decay + positive sentiment → users learned it, stopped searching"
            }
        elif high_decay and negative:
            return {
                "classification": "ABANDONMENT",
                "explanation": "High decay + negative sentiment → users tried it, gave up"
            }
        elif low_decay and positive:
            return {
                "classification": "SUSTAINED_INTEREST",
                "explanation": "Low decay + positive sentiment → true ongoing interest (rare)"
            }
        elif high_decay and sentiment["total_mentions"] < 10:
            return {
                "classification": "LOW_AWARENESS",
                "explanation": "High decay + few mentions → never gained traction"
            }
        else:
            return {
                "classification": "UNCERTAIN",
                "explanation": f"Mixed signals: {search_decay:.1%} decay, {sentiment['sentiment_label']} sentiment, {sentiment['total_mentions']} mentions"
            }

    def validate_feature(self, feature_name: str, company: str, launch_date: str,
                        search_keywords: List[str], search_decay: Optional[float]) -> Dict:
        """
        Run full validation pipeline: search Reddit → analyze sentiment → classify.
        Returns dict with all validation results.
        """
        print(f"\n{'='*80}")
        print(f"🔍 VALIDATING: {feature_name} ({company})")
        print(f"{'='*80}")

        mentions = self.search_feature_mentions(feature_name, company, launch_date, search_keywords)
        sentiment = self.analyze_sentiment(mentions)
        classification = self.classify_feature(search_decay, sentiment)

        return {
            "feature_name": feature_name,
            "company": company,
            "launch_date": launch_date,
            "search_decay": search_decay if search_decay is not None else float("nan"),
            **sentiment,
            **classification
        }
