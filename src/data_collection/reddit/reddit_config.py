"""
Configuration for Reddit sentiment validation.

Contains feature mappings, company guardrails, keyword expansions, and subreddit
mappings for validating subscription feature success through Reddit analysis.

Product Analyst Context:
    These configurations prevent data contamination when analyzing similar features
    across different products (e.g., YouTube TV vs YouTube Premium), and provide
    keyword expansions that match how users naturally discuss features on Reddit.
"""

from typing import Dict, List


# =============================================================================
# FEATURE OVERRIDES
# =============================================================================

# Optional overrides for known features:
# - Fill in company when CSV has "Unknown"
# - Add richer keyword sets when needed
FEATURE_OVERRIDES: Dict[str, Dict] = {
    "Password Sharing Crackdown": {
        "company": "Netflix",
        "keywords": ["password sharing", "account sharing", "netflix password"],
    },
    "AI DJ": {
        "company": "Spotify",
        "keywords": ["AI DJ", "spotify dj", "ai generated playlist"],
    },
    "Ad-Supported Tier": {
        "company": "Netflix",
        "keywords": ["netflix ads", "ad tier", "basic with ads"],
    },
    "GroupWatch": {
        "company": "Disney+",
        "keywords": ["groupwatch", "watch party", "disney plus together"],
    },
    "Games": {
        "company": "Netflix",
        "keywords": ["netflix games", "mobile games"],
    },
}


# =============================================================================
# FEATURE COMPANY GUARDS
# =============================================================================

# Guardrails for "risky" features that must belong to specific products.
# This prevents ambiguous mappings across umbrella brands (e.g. YouTube TV vs YouTube Premium).
#
# Business Logic:
#   When analyzing engagement data, features like "Multiview" should ONLY be attributed
#   to YouTube TV, not YouTube Premium. Without these guards, keyword inference could
#   incorrectly map features across products, contaminating our analysis.
FEATURE_COMPANY_GUARDS: Dict[str, List[str]] = {
    # YouTube ecosystem
    "Offline Downloads": ["YouTube Premium"],
    "Background Play": ["YouTube Premium"],
    "Queue Management": ["YouTube Premium"],
    "Premium Lite": ["YouTube"],  # if you ever treat generic YouTube separately

    "Unlimited DVR": ["YouTube TV"],
    "Multiview": ["YouTube TV"],
    "NFL Sunday Ticket": ["YouTube TV"],

    # Disney bundle (Disney+ vs Hulu)
    "GroupWatch": ["Disney+"],   # Disney+ social feature
    "Watch Party": ["Hulu"],     # Hulu co-viewing feature

    # Offline features across SVODs (avoid cross-wiring)
    "Downloads Offline": ["Disney+"],             # Disney+ core feature
    "Download to Watch Offline": ["Paramount+"],  # Paramount+ core feature

    # X / Twitter
    "X Premium Blue": ["Twitter/X"],
    "Grok AI": ["Twitter/X"],
    "Longer Videos": ["Twitter/X"],

    # Paramount / Showtime integration
    "Showtime Integration": ["Paramount+"],

    # Apple Music audio tech
    "Dolby Atmos": ["Apple Music"],
    "Lossless Audio": ["Apple Music"],

    # Spotify AI stuff
    "AI DJ": ["Spotify"],
    "AI Playlist": ["Spotify"],
    "Wrapped AI Podcast": ["Spotify"],
}


# =============================================================================
# SEARCH LIMITS
# =============================================================================

# Hard cap for how many Reddit search queries we run per feature.
#
# Why this matters:
#   Reddit's API has rate limits. Each keyword = 1+ API call. Running 20 keywords
#   per feature across 40+ features = hitting rate limits fast. This cap balances
#   search coverage with API constraints.
MAX_KEYWORDS_PER_FEATURE = 8


# =============================================================================
# FEATURE EXPANSIONS
# =============================================================================

# Token → expansion lists used by generate_keywords() to create Reddit search queries.
#
# Design Philosophy:
#   Users don't search for "AI DJ" using corporate feature names. They use natural
#   language like "spotify dj", "ai playlist", "algorithm". These expansions capture
#   how people actually discuss features on Reddit.
FEATURE_EXPANSIONS: Dict[str, List[str]] = {
    "ai": ["ai", "artificial intelligence", "ai feature", "ai generated", "algorithm"],
    "playlist": ["playlist", "auto playlist", "personalized playlist", "dynamic playlist"],
    "offline": ["offline", "offline mode", "watch offline", "offline playback", "download offline"],
    "downloads": ["download", "downloads", "download feature", "offline viewing"],
    "password_sharing": [
        "password sharing",
        "account sharing",
        "extra member",
        "household",
        "sharing ban",
        "device limit",
    ],
    "ads": ["ad tier", "with ads", "ads plan", "basic with ads"],
    "audio_spatial": ["spatial audio", "3d audio", "spatial sound", "sound upgrade", "enhanced audio"],
    "gaming": ["games", "gaming", "mobile games", "game library"],
    "queue": ["queue", "playlist queue", "queue feature", "add to queue", "how to queue"],
    "background_play": ["background play", "play in background", "background audio"],
    "dvr": ["dvr", "cloud dvr", "recordings", "record shows", "record tv"],
    "multiview": ["multiview", "multi-view", "4 streams", "multiple screens"],
    "price_increase": ["price increase", "price hike", "pricing change", "higher price"],
    "watch_party": ["watch party", "groupwatch", "co-watch", "party mode"],
    "lossless": ["lossless", "hi-res", "alac", "high fidelity", "lossless audio"],
    "atmos": ["atmos", "dolby atmos", "spatial audio", "3d sound"],
    "karaoke": ["karaoke", "sing", "lyrics mode", "sing along"],
    "classical": ["classical app", "classical music", "apple classical", "classical streaming"],
    "showtime": ["showtime", "showtime bundle", "showtime integration"],
    "sports": ["sports", "espn", "live sports", "sports content"],
    "twitter_premium": ["twitter blue", "x premium", "premium tier", "verification"],
    "grok": ["grok", "grok ai", "x ai", "elon ai"],
    "video_length": ["long videos", "upload long video", "longer videos", "video length"],
}


# =============================================================================
# COMPANY-TO-SUBREDDIT MAPPINGS
# =============================================================================

# Map company names to their primary subreddits for sentiment analysis.
#
# Selection Criteria:
#   - Active community with regular feature discussions
#   - Official or semi-official subreddit (moderated, on-topic)
#   - Large enough for meaningful sample sizes
COMPANY_SUBREDDITS: Dict[str, str] = {
    "Netflix": "netflix",
    "Spotify": "spotify",
    "Disney+": "DisneyPlus",
    "YouTube Premium": "youtube",
    "YouTube TV": "youtubetv",
    "Hulu": "Hulu",
    "Apple Music": "AppleMusic",
    "Paramount+": "ParamountPlus",
    "Peloton": "pelotoncycle",
    "Twitter/X": "Twitter",
}