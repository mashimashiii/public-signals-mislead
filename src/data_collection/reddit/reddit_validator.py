"""
Reddit sentiment validation for feature launches.

Core validation logic that combines Reddit mentions + sentiment analysis with Google
Trends decay data to classify feature adoption patterns. Implements the decision
framework for distinguishing feature success from failure based on external signals.

Classification Logic:
    - High decay + positive sentiment + high mentions = ADOPTION (learned, stopped searching)
    - High decay + negative sentiment = ABANDONMENT (tried, gave up)
    - Low decay + positive sentiment = SUSTAINED_INTEREST (rare)
    - High decay + very few mentions = LOW_AWARENESS (never gained traction)
    - Missing decay metrics = NO_DECAY_DATA (sentiment still reported)
    - Everything else = UNCERTAIN (mixed signals)

Product Analyst Context:
    This is the "multi-signal validation" approach that addresses the core finding:
    search decay alone cannot distinguish adoption from abandonment. We need Reddit
    sentiment to interpret what the decay pattern actually means.
"""

import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import Counter
import time

import pandas as pd

from .reddit_config import (
    FEATURE_OVERRIDES,
    FEATURE_COMPANY_GUARDS,
    FEATURE_EXPANSIONS,
    MAX_KEYWORDS_PER_FEATURE,
    COMPANY_SUBREDDITS,
)
from .reddit_clients import BaseRedditClient, PrawRedditClient, PublicRedditClient

try:
    import praw  # Optional: only required for authenticated mode
except ImportError:
    praw = None


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def infer_company_from_keyword(keyword: Optional[str]) -> Optional[str]:
    """
    Infer canonical company name from the 'keyword' field in MERGED_trends_data.csv.
    
    Why this matters:
        The trends CSV might have missing company data, but the keyword field usually
        contains company names (e.g., "Spotify AI DJ", "Netflix password sharing").
        This function extracts the company using pattern matching.
    
    Keyword examples:
        - 'Spotify AI DJ' → 'Spotify'
        - 'Netflix password sharing' → 'Netflix'
        - 'Disney Plus GroupWatch' → 'Disney+'
        - 'YouTube background play' → 'YouTube Premium'
        - 'YouTube TV DVR' → 'YouTube TV'
        - 'Paramount Plus downloads' → 'Paramount+'
        - 'Apple Music Classical' → 'Apple Music'
        - 'Peloton running' → 'Peloton'
        - 'Hulu Watch Party' → 'Hulu'
        - 'X Grok AI' → 'Twitter/X'

    Args:
        keyword: Keyword string from trends data CSV.

    Returns:
        Canonical company name matching RedditValidator.subreddits keys,
        or None if not detected.
    """
    if not isinstance(keyword, str):
        return None

    k = keyword.lower().strip()

    # Order matters: check more specific patterns first to avoid false positives
    # (e.g., "YouTube TV" must be checked before "YouTube")
    
    if "spotify" in k:
        return "Spotify"

    if "netflix" in k:
        return "Netflix"

    if "disney plus" in k or "disney+" in k:
        return "Disney+"

    # YouTube ecosystem - must check YouTube TV before generic YouTube
    if "youtube tv" in k:
        return "YouTube TV"

    if "youtube" in k:
        # Generic YouTube product features → search in r/youtube
        return "YouTube Premium"

    if "apple music" in k:
        return "Apple Music"

    if "peloton" in k:
        return "Peloton"

    if "paramount plus" in k:
        return "Paramount+"

    if "paramount" in k:
        # 'Paramount Showtime', etc. - map to Paramount+
        return "Paramount+"

    if "hulu" in k:
        return "Hulu"

    # X / Twitter - multiple possible patterns
    if k.startswith("x ") or " x " in k or "grok ai" in k:
        return "Twitter/X"
    if "twitter" in k:
        return "Twitter/X"

    return None


def enforce_feature_company_guard(
    feature_name: str,
    company: str,
) -> bool:
    """
    Enforce guardrails for "risky" features that must belong to specific products.

    Business Logic:
        Some feature names (like "Multiview") could apply to multiple products, but
        should only be analyzed for specific ones. Without guards, keyword-based
        company inference might map features incorrectly, mixing data from YouTube TV
        with YouTube Premium, or Disney+ with Hulu.
        
        This function checks FEATURE_COMPANY_GUARDS to ensure features are only
        analyzed for their intended products.

    Example:
        enforce_feature_company_guard("Multiview", "YouTube TV") → True
        enforce_feature_company_guard("Multiview", "YouTube Premium") → False
        
    Args:
        feature_name: Name of the feature (as in the metrics CSV).
        company: Resolved company name (after overrides / inference).

    Returns:
        True if this (feature_name, company) combination passes guardrail checks,
        False if it violates guards (feature should be skipped to avoid contamination).
    """
    allowed = FEATURE_COMPANY_GUARDS.get(feature_name)
    if not allowed:
        # No guard defined → nothing to enforce
        return True

    if company in allowed:
        return True

    # Guardrail violation - warn and reject
    print(
        f"⚠️  Guardrail: feature '{feature_name}' is expected to belong to "
        f"{allowed}, but resolved company='{company}'. Skipping to avoid "
        f"cross-product mixing (umbrella brand confusion)."
    )
    return False


def is_twitter_premium_feature(feature_name: str) -> bool:
    """
    Heuristic: return True if the feature name looks like a Twitter/X
    paid tier / subscription change (e.g., Twitter Blue, X Premium).

    Why this matters:
        For Twitter/X features, we need to distinguish between:
        - Premium tier features (X Premium Blue) → Add "twitter blue", "x premium" keywords
        - Product features (Grok AI, Longer Videos) → Don't pollute with generic tier keywords
        
        Without this check, searching for "Grok AI" might return irrelevant posts about
        Twitter Blue pricing changes.
        
    Args:
        feature_name: Feature name to check.
        
    Returns:
        True if feature appears to be a premium tier feature, False otherwise.
    """
    name = feature_name.lower()
    premium_markers = [
        "premium",
        "blue",
        "x premium",
        "x blue",
        "subscription",
        "subscribers",  # optional, safe-ish
    ]
    return any(marker in name for marker in premium_markers)


def generate_keywords(feature_name: str, company: str) -> List[str]:
    """
    Generate a compact set of Reddit search keywords from a feature name and company.

    Design Goals:
        1. Keep the number of API calls small (rate-limit friendly)
        2. Still capture the main ways people might talk about the feature
        3. Avoid combinatorial explosion from complaint patterns
        
    Strategy:
        - Start with base patterns (feature name, company + feature, lowercase variants)
        - Add light token-level expansions (if tokens match FEATURE_EXPANSIONS keys)
        - Add company-specific generic terms (e.g., "youtube premium", "spotify")
        - Deduplicate and cap at MAX_KEYWORDS_PER_FEATURE (default 8)

    Why not just use the feature name?
        Users rarely search Reddit using exact corporate feature names. For "Offline
        Downloads", they might say "download offline", "watch offline", "offline mode".
        These expansions capture natural language variations.

    Logic:
        - Base patterns:
            - feature_name (e.g., "Offline Downloads")
            - "Company feature_name" (e.g., "YouTube Premium Offline Downloads")
            - Lowercase variants
        - Light token expansions (if tokens match FEATURE_EXPANSIONS keys):
            - Take at most 2 expansions per token
            - Only expand the first 2 matching tokens (avoid explosion)
        - Company-specific terms (e.g., "youtube premium", "yt premium")
        - No complaint-style permutations (too many variations, low signal)
        - Deduplicate and hard-cap to MAX_KEYWORDS_PER_FEATURE

    Args:
        feature_name: Human-readable feature name.
        company: Company name (used both in text and for platform-specific expansions).

    Returns:
        List of keyword strings to use in Reddit search (max MAX_KEYWORDS_PER_FEATURE).
    """
    fn = feature_name.lower()
    kw: List[str] = []

    # --- Base patterns ---
    kw += [
        feature_name,                          # "Offline Downloads"
        f"{company} {feature_name}",           # "YouTube Premium Offline Downloads"
        feature_name.lower(),                  # "offline downloads"
        f"{company.lower()} {feature_name.lower()}",
    ]

    # --- Light token-level expansions ---
    tokens = fn.split()
    expanded_tokens = 0

    for token in tokens:
        if token in FEATURE_EXPANSIONS:
            # Only expand up to 2 tokens to avoid explosion
            if expanded_tokens >= 2:
                break

            expansions = FEATURE_EXPANSIONS[token][:2]  # at most 2 per token
            kw.extend(expansions)
            expanded_tokens += 1

    # --- Company-specific generic terms (very small set) ---
    if company == "Spotify":
        pass  # No additional generic terms needed
    elif company == "Netflix":
        pass  # No additional generic terms needed
    elif company == "YouTube Premium":
        kw += ["youtube premium", "yt premium"]
    elif company == "YouTube TV":
        kw += ["youtube tv"]
    elif company == "Disney+":
        kw += ["disney plus"]
    elif company == "Paramount+":
        kw += ["paramount plus"]
    elif company == "Apple Music":
        kw += ["apple music"]
    elif company == "Peloton":
        kw += ["peloton app"]
    elif company in ["X Premium", "Twitter/X"]:
        # Only add generic premium queries for actual tier / subscription features
        # This prevents polluting "Grok AI" searches with "twitter blue" results
        if is_twitter_premium_feature(feature_name):
            kw += ["twitter blue", "x premium"]

    # --- Deduplicate while preserving order ---
    kw = list(dict.fromkeys(kw))

    # --- Hard cap total queries per feature ---
    if len(kw) > MAX_KEYWORDS_PER_FEATURE:
        kw = kw[:MAX_KEYWORDS_PER_FEATURE]

    return kw


# =============================================================================
# MAIN VALIDATOR CLASS
# =============================================================================


class RedditValidator:
    """
    Validate feature success by analyzing Reddit sentiment and mention volume.

    Core Workflow:
        1. Generate search keywords for feature
        2. Search Reddit for mentions in relevant subreddit
        3. Analyze sentiment from posts/comments
        4. Combine with Google Trends decay data
        5. Classify as ADOPTION / ABANDONMENT / SUSTAINED_INTEREST / etc.

    Attributes:
        client: Reddit client implementation (PRAW or public JSON).
        subreddits: Dict mapping companies to their primary subreddits.
    """

    def __init__(self, client: Optional[BaseRedditClient] = None):
        """
        Initialize Reddit client.

        Client Selection Logic:
            1. If client is provided explicitly, use it
            2. Else, try to initialize PRAW using environment variables
            3. If PRAW credentials unavailable, fall back to PublicRedditClient
            
        Environment Variables (for PRAW):
            - REDDIT_CLIENT_ID
            - REDDIT_CLIENT_SECRET
            - REDDIT_USERNAME
            - REDDIT_PASSWORD
            - REDDIT_USER_AGENT (optional, defaults to "subscription-feature-analysis/1.0")
            
        Args:
            client: Optional pre-configured Reddit client. If None, will auto-detect.
        """
        # Map companies to their primary subreddits
        self.subreddits: Dict[str, str] = COMPANY_SUBREDDITS

        if client is not None:
            self.client = client
            print("✅ Using custom Reddit client.")
            return

        # Try authenticated PRAW client first
        client_id = os.getenv("REDDIT_CLIENT_ID")
        client_secret = os.getenv("REDDIT_CLIENT_SECRET")
        username = os.getenv("REDDIT_USERNAME")
        password = os.getenv("REDDIT_PASSWORD")
        user_agent = os.getenv(
            "REDDIT_USER_AGENT", "subscription-feature-analysis/1.0"
        )

        if (
            praw is not None
            and client_id
            and client_secret
            and username
            and password
        ):
            print("✅ Using PRAW Reddit client (authenticated mode).")
            reddit = praw.Reddit(
                client_id=client_id,
                client_secret=client_secret,
                username=username,
                password=password,
                user_agent=user_agent,
            )
            self.client = PrawRedditClient(reddit)
        else:
            print(
                "⚠️  Reddit API credentials or PRAW not available. "
                "Falling back to public JSON client (no API keys)."
            )
            self.client = PublicRedditClient(
                user_agent="feature-sentiment-valid-unauth/1.0"
            )

    def search_feature_mentions(
        self,
        feature_name: str,
        company: str,
        launch_date: str,
        search_keywords: List[str],
        weeks_after: int = 12,
    ) -> List[Dict]:
        """
        Search Reddit for mentions of a feature within a post-launch timeframe.

        Time Window Strategy:
            Default to 12 weeks post-launch. This captures the critical adoption period
            while avoiding noise from much later discussions (e.g., anniversary posts,
            retrospectives).
            
        Why 12 weeks:
            - Most features show peak engagement within 4-8 weeks
            - 12 weeks gives buffer for slower-building features
            - Matches Google Trends week_8 metric timeframe
            
        Args:
            feature_name: Human-readable feature name.
            company: Company name (maps to subreddit).
            launch_date: Feature launch date (YYYY-MM-DD).
            search_keywords: List of search terms for Reddit search.
            weeks_after: Number of weeks post-launch to search (default 12).

        Returns:
            List of Reddit mentions (posts and optionally comments) with metadata.
        """
        if company not in self.subreddits:
            print(f"⚠️  No subreddit mapping for {company} – skipping.")
            return []

        subreddit_name = self.subreddits[company]

        # Calculate time window
        launch = datetime.strptime(launch_date, "%Y-%m-%d")
        end_date = launch + timedelta(weeks=weeks_after)
        launch_timestamp = int(launch.timestamp())
        end_timestamp = int(end_date.timestamp())

        mentions: List[Dict] = []

        for keyword in search_keywords:
            print(f"  🔍 Searching r/{subreddit_name} for '{keyword}'...")

            try:
                keyword_mentions = self.client.search_mentions(
                    subreddit=subreddit_name,
                    keyword=keyword,
                    start_ts=launch_timestamp,
                    end_ts=end_timestamp,
                    comment_limit=10,
                    max_posts=100,
                )
                for m in keyword_mentions:
                    m.setdefault("keyword", keyword)
                    m.setdefault("subreddit", subreddit_name)
                mentions.extend(keyword_mentions)
                # Light rate limiting handled in client; extra pause here is safe
                time.sleep(1.0)
            except Exception as e:
                print(f"  ❌ Error searching '{keyword}': {str(e)}")

        print(f"  ✅ Found {len(mentions)} mentions")
        return mentions

    def analyze_sentiment(self, mentions: List[Dict]) -> Dict[str, float]:
        """
        Analyze sentiment from Reddit mentions using a simple keyword-based approach.

        Methodology:
            This is a lightweight heuristic sentiment model using positive/negative
            keyword matching. It's fast and surprisingly effective for product feature
            discussions, where sentiment is often explicit ("love it", "hate it", "bug").
            
        Limitations:
            - Doesn't handle sarcasm well
            - Misses context-dependent sentiment
            - No intensity weighting
            
        For Production:
            Consider transformer-based models (e.g., RoBERTa sentiment, VADER) for
            more nuanced sentiment analysis. However, keyword-based is sufficient for
            the current use case of distinguishing broadly positive vs negative reception.

        Args:
            mentions: List of Reddit posts/comments with 'title' and 'text' fields.

        Returns:
            Dictionary with sentiment metrics:
                - total_mentions: Count of analyzed posts/comments
                - positive_ratio: Proportion classified as positive (0-1)
                - negative_ratio: Proportion classified as negative (0-1)
                - neutral_ratio: Proportion classified as neutral (0-1)
                - avg_score: Average Reddit score (upvotes)
                - sentiment_label: Overall label ("positive", "negative", or "mixed")
                - positive_count: Raw count of positive mentions
                - negative_count: Raw count of negative mentions
                - neutral_count: Raw count of neutral mentions
        """
        if not mentions:
            return {
                "total_mentions": 0,
                "positive_ratio": 0.0,
                "negative_ratio": 0.0,
                "neutral_ratio": 0.0,
                "avg_score": 0.0,
                "sentiment_label": "unknown",
            }

        # Keyword lists - selected for product feature discussions
        positive_keywords = [
            "love",
            "great",
            "awesome",
            "perfect",
            "amazing",
            "excellent",
            "fantastic",
            "helpful",
            "useful",
            "convenient",
            "easy",
            "better",
            "impressed",
            "glad",
            "finally",  # Often used positively: "finally a good feature"
            "appreciate",
            "worth",
        ]

        negative_keywords = [
            "hate",
            "terrible",
            "awful",
            "worst",
            "horrible",
            "useless",
            "annoying",
            "frustrating",
            "disappointed",
            "regret",
            "waste",
            "broken",
            "bug",
            "issue",
            "problem",
            "cancel",  # Strong negative signal in subscription context
            "unsubscribe",
        ]

        sentiments: List[str] = []
        scores: List[float] = []

        for mention in mentions:
            text = f"{mention.get('title', '')} {mention.get('text', '')}".lower()

            positive_count = sum(1 for word in positive_keywords if word in text)
            negative_count = sum(1 for word in negative_keywords if word in text)

            # Simple majority voting
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

        # Overall label - requires >50% for positive/negative, else "mixed"
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
            "neutral_count": sentiment_counts["neutral"],
        }

    def classify_feature(
        self,
        search_decay: Optional[float],
        sentiment: Dict,
    ) -> Dict[str, str]:
        """
        Classify a feature based on search decay + sentiment signals.
        
        This is the core decision logic that implements the multi-signal validation
        framework. Search decay alone is ambiguous - it could mean adoption (users
        learned the feature) or abandonment (users gave up). Reddit sentiment breaks
        the tie.

        Classification Logic:
            - High decay (>70%) + Positive sentiment + High mentions = ADOPTION
                → Users learned the feature, stopped searching (positive outcome)
                
            - High decay (>70%) + Negative sentiment = ABANDONMENT
                → Users tried the feature but gave up (negative outcome)
                
            - Low decay (<30%) + Positive sentiment = SUSTAINED_INTEREST
                → Rare case: true ongoing interest (e.g., Netflix password crackdown)
                
            - High decay + very few mentions (<10) = LOW_AWARENESS
                → Feature never gained traction, low public awareness
                
            - Missing decay metrics = NO_DECAY_DATA
                → Can't classify adoption vs abandonment without decay data,
                  but sentiment and mention volume are still reported
                  
            - Else = UNCERTAIN
                → Mixed signals that don't fit clear patterns

        Args:
            search_decay: Decay rate from Google Trends (0–1), or None if unavailable.
            sentiment: Sentiment metrics from Reddit (from analyze_sentiment()).

        Returns:
            Dictionary with classification:
                - classification: Label (ADOPTION, ABANDONMENT, etc.)
                - explanation: Human-readable explanation of the classification
        """
        if search_decay is None or pd.isna(search_decay):
            return {
                "classification": "NO_DECAY_DATA",
                "explanation": (
                    "Trend decay metrics (week_4/week_8) are not available yet "
                    "for this feature, so we cannot classify adoption vs abandonment. "
                    "Reddit sentiment and mention volume are still reported."
                ),
            }

        # Define thresholds
        high_decay = search_decay > 0.70
        low_decay = search_decay < 0.30
        positive = sentiment["sentiment_label"] == "positive"
        negative = sentiment["sentiment_label"] == "negative"
        high_mentions = sentiment["total_mentions"] > 20  # Arbitrary but reasonable

        # Apply classification rules
        if high_decay and positive and high_mentions:
            return {
                "classification": "ADOPTION",
                "explanation": (
                    "High search decay but positive Reddit sentiment suggests users "
                    "learned the feature and adopted it (stopped searching)."
                ),
            }
        elif high_decay and negative:
            return {
                "classification": "ABANDONMENT",
                "explanation": (
                    "High search decay with negative sentiment indicates users tried "
                    "the feature but gave up."
                ),
            }
        elif low_decay and positive:
            return {
                "classification": "SUSTAINED_INTEREST",
                "explanation": (
                    "Low search decay with positive sentiment shows true ongoing "
                    "interest (rare)."
                ),
            }
        elif high_decay and sentiment["total_mentions"] < 10:
            return {
                "classification": "LOW_AWARENESS",
                "explanation": (
                    "High search decay with few Reddit mentions suggests the feature "
                    "never gained traction."
                ),
            }
        else:
            return {
                "classification": "UNCERTAIN",
                "explanation": (
                    f"Mixed signals: {search_decay:.1%} decay, "
                    f"{sentiment['sentiment_label']} sentiment, "
                    f"{sentiment['total_mentions']} mentions."
                ),
            }

    def validate_feature(
        self,
        feature_name: str,
        company: str,
        launch_date: str,
        search_keywords: List[str],
        search_decay: Optional[float],
    ) -> Dict:
        """
        Run the full validation pipeline for a single feature.
        
        Pipeline:
            1. Search Reddit for feature mentions using keywords
            2. Analyze sentiment from mentions
            3. Classify based on decay + sentiment
            4. Return structured results

        Args:
            feature_name: Feature name.
            company: Company name.
            launch_date: Launch date (YYYY-MM-DD).
            search_keywords: Keywords to search for on Reddit.
            search_decay: Search decay rate from Google Trends (0–1), or None.

        Returns:
            Dictionary with complete validation results:
                - feature_name, company, launch_date
                - search_decay
                - All sentiment metrics (positive_ratio, negative_ratio, etc.)
                - classification, explanation
        """
        print("\n" + "=" * 80)
        print(f"🔍 VALIDATING: {feature_name} ({company})")
        print("=" * 80)

        mentions = self.search_feature_mentions(
            feature_name=feature_name,
            company=company,
            launch_date=launch_date,
            search_keywords=search_keywords,
        )

        sentiment = self.analyze_sentiment(mentions)
        classification = self.classify_feature(search_decay, sentiment)

        return {
            "feature_name": feature_name,
            "company": company,
            "launch_date": launch_date,
            "search_decay": search_decay if search_decay is not None else float("nan"),
            **sentiment,
            **classification,
        }