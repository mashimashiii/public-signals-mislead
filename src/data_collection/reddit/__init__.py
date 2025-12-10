"""
Reddit sentiment validation package for subscription features.

Provides modular components for validating feature success using Reddit mentions
and sentiment analysis combined with Google Trends decay data.

Modules:
    - reddit_config: Configuration constants and mappings
    - reddit_clients: API client implementations (PRAW and public JSON)
    - reddit_validator: Core validation logic and classification
    - validate_features: CLI script for running validation

Quick Start:
    ```python
    from src.data_collection.reddit import RedditValidator
    
    # Initialize with auto-detected client
    validator = RedditValidator()
    
    # Validate a single feature
    result = validator.validate_feature(
        feature_name="AI DJ",
        company="Spotify",
        launch_date="2023-02-22",
        search_keywords=["ai dj", "spotify dj"],
        search_decay=0.89
    )
    ```
    
    Or use the CLI:
    ```bash
    python -m src.data_collection.reddit.validate_features --companies "Netflix,Spotify"
    ```
"""

from .reddit_config import (
    FEATURE_OVERRIDES,
    FEATURE_COMPANY_GUARDS,
    FEATURE_EXPANSIONS,
    MAX_KEYWORDS_PER_FEATURE,
    COMPANY_SUBREDDITS,
)

from .reddit_clients import (
    BaseRedditClient,
    PrawRedditClient,
    PublicRedditClient,
)

from .reddit_validator import (
    RedditValidator,
    infer_company_from_keyword,
    enforce_feature_company_guard,
    is_twitter_premium_feature,
    generate_keywords,
)

__all__ = [
    # Config
    "FEATURE_OVERRIDES",
    "FEATURE_COMPANY_GUARDS",
    "FEATURE_EXPANSIONS",
    "MAX_KEYWORDS_PER_FEATURE",
    "COMPANY_SUBREDDITS",
    # Clients
    "BaseRedditClient",
    "PrawRedditClient",
    "PublicRedditClient",
    # Validator
    "RedditValidator",
    "infer_company_from_keyword",
    "enforce_feature_company_guard",
    "is_twitter_premium_feature",
    "generate_keywords",
]