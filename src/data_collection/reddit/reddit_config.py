"""
Configuration for Reddit sentiment validation.

Contains feature mappings, company guardrails, keyword expansions, and subreddit mappings.
These prevent data contamination when analyzing similar features across different products.
"""

from typing import Dict, List


# Optional overrides for features with known company or richer keyword sets
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


# Guardrails for features that must belong to specific products
# Prevents ambiguous mappings across umbrella brands (YouTube TV vs YouTube Premium)
FEATURE_COMPANY_GUARDS: Dict[str, List[str]] = {
    # YouTube ecosystem
    "Offline Downloads": ["YouTube Premium"],
    "Background Play": ["YouTube Premium"],
    "Queue Management": ["YouTube Premium"],
    "Premium Lite": ["YouTube"],
    
    "Unlimited DVR": ["YouTube TV"],
    "Multiview": ["YouTube TV"],
    "NFL Sunday Ticket": ["YouTube TV"],

    # Disney bundle
    "GroupWatch": ["Disney+"],
    "Watch Party": ["Hulu"],

    # Avoid cross-wiring offline features
    "Downloads Offline": ["Disney+"],
    "Download to Watch Offline": ["Paramount+"],

    # X / Twitter
    "X Premium Blue": ["Twitter/X"],
    "Grok AI": ["Twitter/X"],
    "Longer Videos": ["Twitter/X"],

    "Showtime Integration": ["Paramount+"],

    # Apple Music audio tech
    "Dolby Atmos": ["Apple Music"],
    "Lossless Audio": ["Apple Music"],

    # Spotify AI
    "AI DJ": ["Spotify"],
    "AI Playlist": ["Spotify"],
    "Wrapped AI Podcast": ["Spotify"],
}


# Hard cap for Reddit search queries per feature (API rate limits)
MAX_KEYWORDS_PER_FEATURE = 8


# Token expansions for generating Reddit search queries
# Users don't search using corporate feature names - they use natural language
FEATURE_EXPANSIONS: Dict[str, List[str]] = {
    "ai": ["ai", "artificial intelligence", "ai feature", "ai generated", "algorithm"],
    "playlist": ["playlist", "auto playlist", "personalized playlist", "dynamic playlist"],
    "offline": ["offline", "offline mode", "watch offline", "offline playback", "download offline"],
    "downloads": ["download", "downloads", "download feature", "offline viewing"],
    "password_sharing": [
        "password sharing", "account sharing", "extra member", "household", 
        "sharing ban", "device limit"
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


# Map company names to primary subreddits for sentiment analysis
# Selection criteria: active community, official/semi-official, large enough sample
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
