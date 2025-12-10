"""
Configuration: Known Business Outcomes

This file contains verified business outcomes for features with public metrics.
All metrics sourced from earnings calls, press releases, or credible third-party reports.

Last updated: December 2025
"""

# Known business outcomes with verifiable metrics
KNOWN_OUTCOMES = {
    # ========================================================================
    # TIER 1: STRONG SUCCESS (Hard metrics from official sources)
    # ========================================================================
    'Password Sharing Crackdown': {
        'outcome': 'SUCCESS',
        'metric': '9.3M paid net additions (Q1 2024)',
        'source': 'Netflix Q1 2024 shareholder letter',
        'tier': 'TIER1',
        'url': 'https://ir.netflix.net/financials/quarterly-earnings/default.aspx'
    },
    'Extra Member': {
        'outcome': 'SUCCESS',
        'metric': 'Contributed to 9.3M growth',
        'source': 'Netflix Q1 2024 shareholder letter',
        'tier': 'TIER1',
        'url': 'https://ir.netflix.net/financials/quarterly-earnings/default.aspx'
    },
    'Ad-Supported Tier': {
        'outcome': 'SUCCESS',
        'metric': '23M monthly active users (Jan 2024)',
        'source': 'Netflix press release',
        'tier': 'TIER1',
        'url': 'https://about.netflix.com/en/news/netflix-ads-plan-grows'
    },
    'AI DJ': {
        'outcome': 'SUCCESS',
        'metric': 'Billions of streams, top engagement driver',
        'source': 'Spotify Q4 2023 shareholder letter',
        'tier': 'TIER1',
        'url': 'https://investors.spotify.com'
    },
    'Premium Price Increase': {
        'outcome': 'SUCCESS',
        'metric': '10% ARPU increase YoY',
        'source': 'Spotify Q3 2023 earnings call',
        'tier': 'TIER1',
        'url': 'https://investors.spotify.com/financials/press-releases/default.aspx'
    },
    'Multiview': {
        'outcome': 'SUCCESS',
        'metric': 'Millions of viewers during NFL',
        'source': 'YouTube Blog',
        'tier': 'TIER1',
        'url': 'https://blog.youtube/news-and-events/nfl-sunday-ticket-youtube-tv/'
    },
    'Strength Training': {
        'outcome': 'SUCCESS',
        'metric': '32% YoY growth in minutes consumed',
        'source': 'Peloton Shareholder Letter 2022',
        'tier': 'TIER1',
        'url': 'https://investor.onepeloton.com'
    },
    
    # ========================================================================
    # TIER 2: MODERATE SUCCESS (Directional evidence, no hard numbers)
    # ========================================================================
    'Audiobooks': {
        'outcome': 'MODERATE_SUCCESS',
        'metric': 'Increased retention and listening hours',
        'source': 'Spotify Q3 2023 earnings',
        'tier': 'TIER2',
        'url': 'https://investors.spotify.com'
    },
    'Star Content Hub': {
        'outcome': 'MODERATE_SUCCESS',
        'metric': 'Higher engagement in EU markets',
        'source': 'Disney 2021 Investor Day',
        'tier': 'TIER2',
        'url': 'https://thewaltdisneycompany.com/disney-investor-day-2020/'
    },
    'IMAX Enhanced': {
        'outcome': 'MODERATE_SUCCESS',
        'metric': 'High viewership for Marvel titles',
        'source': 'Disney press release',
        'tier': 'TIER2',
        'url': None
    },
    'Unlimited DVR': {
        'outcome': 'MODERATE_SUCCESS',
        'metric': '#1 reason for switching to YouTube TV',
        'source': 'YouTube TV marketing',
        'tier': 'TIER2',
        'url': None
    },
    'Background Play': {
        'outcome': 'MODERATE_SUCCESS',
        'metric': 'Top retention driver for Premium',
        'source': 'YouTube Premium interviews',
        'tier': 'TIER2',
        'url': None
    },
    'Offline Downloads': {
        'outcome': 'MODERATE_SUCCESS',
        'metric': 'Top 3 most-used Premium feature',
        'source': 'YouTube Premium interviews',
        'tier': 'TIER2',
        'url': None
    },
    'Classical App': {
        'outcome': 'MODERATE_SUCCESS',
        'metric': 'Strong interest among classical listeners',
        'source': 'Apple press release',
        'tier': 'TIER2',
        'url': 'https://www.apple.com/newsroom/'
    },
    'Live TV Cloud DVR': {
        'outcome': 'MODERATE_SUCCESS',
        'metric': 'Top differentiator for churn reduction',
        'source': 'Disney earnings (Hulu segment)',
        'tier': 'TIER2',
        'url': None
    },
    'Running Content': {
        'outcome': 'MODERATE_SUCCESS',
        'metric': 'Top-3 category in outdoor content',
        'source': 'Peloton app updates',
        'tier': 'TIER2',
        'url': None
    },
    
    # ========================================================================
    # TIER 1: CLEAR FAILURES (Discontinued or below expectations)
    # ========================================================================
    'Games': {
        'outcome': 'FAILURE',
        'metric': '<1% daily usage (0.5% of subs)',
        'source': 'CNBC via Apptopia Aug 2023',
        'tier': 'TIER1',
        'url': 'https://www.cnbc.com/2023/08/07/netflix-games-have-low-engagement.html'
    },
    'GroupWatch': {
        'outcome': 'FAILURE',
        'metric': 'Discontinued (removed silently)',
        'source': 'Disney support threads',
        'tier': 'TIER1',
        'url': None
    },
    'Watch Party': {
        'outcome': 'WEAK',
        'metric': 'Low usage (no metrics published)',
        'source': 'Hulu earnings commentary',
        'tier': 'TIER2',
        'url': None
    },
    'App-Only Membership': {
        'outcome': 'FAILURE',
        'metric': 'Below expectations',
        'source': 'Peloton Q4 2023 earnings',
        'tier': 'TIER1',
        'url': 'https://investor.onepeloton.com'
    },
}


# Feature type classification for analysis
FEATURE_TYPES = {
    # Monetization features (pricing, tiers, restrictions)
    'Password Sharing Crackdown': 'MONETIZATION',
    'Extra Member': 'MONETIZATION',
    'Ad-Supported Tier': 'MONETIZATION',
    'Premium Price Increase': 'MONETIZATION',
    'Price Increase': 'MONETIZATION',
    'Premium Plus Tier': 'MONETIZATION',
    
    # AI/Personalization features
    'AI DJ': 'AI',
    'AI Playlist': 'AI',
    'Daylist': 'AI',
    'Wrapped AI Podcast': 'AI',
    'Grok AI': 'AI',
    
    # Content additions (new categories, libraries)
    'Star Content Hub': 'CONTENT',
    'Classical App': 'CONTENT',
    'Audiobooks': 'CONTENT',
    'ESPN Integration': 'CONTENT',
    'Strength Training': 'CONTENT',
    'Rowing Classes': 'CONTENT',
    'Running Content': 'CONTENT',
    
    # Utility/UX improvements
    'Background Play': 'UTILITY',
    'Offline Downloads': 'UTILITY',
    'Downloads Offline': 'UTILITY',
    'Download to Watch Offline': 'UTILITY',
    'Downloads Feature Update': 'UTILITY',
    'Queue Management': 'UTILITY',
    'Profile Transfer': 'UTILITY',
    'Parental Controls Update': 'UTILITY',
    
    # Social/Collaborative features
    'GroupWatch': 'SOCIAL',
    'Watch Party': 'SOCIAL',
    'Multiview': 'SOCIAL',
    
    # Technical quality improvements
    'IMAX Enhanced': 'TECH',
    'Spatial Audio': 'TECH',
    'Lossless Audio': 'TECH',
    'Dolby Atmos': 'TECH',
    'Sing Feature': 'TECH',
    
    # Live/Sports features
    'Live Sports': 'LIVE',
    'Unlimited DVR': 'LIVE',
    'Live TV Cloud DVR': 'LIVE',
    
    # Gaming
    'Games': 'GAMES',
    
    # Other/Uncategorized
    'App-Only Membership': 'OTHER',
}


def get_outcome(feature_name: str) -> dict:
    """
    Get business outcome for a feature.
    
    Args:
        feature_name: Name of the feature
        
    Returns:
        Dictionary with outcome, metric, source, tier
        Empty dict if feature not found
    """
    return KNOWN_OUTCOMES.get(feature_name, {})


def get_feature_type(feature_name: str) -> str:
    """
    Get feature type classification.
    
    Args:
        feature_name: Name of the feature
        
    Returns:
        Feature type string (e.g., 'MONETIZATION', 'AI', 'CONTENT')
        'UNKNOWN' if not classified
    """
    return FEATURE_TYPES.get(feature_name, 'UNKNOWN')


def get_all_labeled_features() -> list:
    """
    Get list of all features with known outcomes.
    
    Returns:
        List of feature names
    """
    return list(KNOWN_OUTCOMES.keys())


def get_success_count() -> dict:
    """
    Count features by outcome type.
    
    Returns:
        Dictionary with counts by outcome type
    """
    counts = {}
    for outcome_data in KNOWN_OUTCOMES.values():
        outcome = outcome_data['outcome']
        counts[outcome] = counts.get(outcome, 0) + 1
    return counts