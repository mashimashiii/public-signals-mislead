"""
Reddit API client implementations.

Two modes:
1. PRAW (authenticated) - higher rate limits, access to comments
2. Public JSON (fallback) - no auth required, posts only, more restrictive

Rate limits are the key constraint. PRAW allows ~60 req/min. Public JSON is ~30 req/min.
"""

from datetime import datetime
from typing import Dict, List, Optional
import time

import requests

try:
    import praw
except ImportError:
    praw = None


class BaseRedditClient:
    """
    Abstract base client for Reddit interface.
    Ensures both PRAW and public JSON clients can be used interchangeably.
    """

    def search_mentions(self, subreddit: str, keyword: str, start_ts: int, end_ts: int,
                       comment_limit: int = 10, max_posts: int = 100) -> List[Dict]:
        """
        Search for mentions of a keyword in a subreddit between timestamps.
        
        Returns list of mention dicts with schema:
        - type: "post" or "comment"
        - title, text, score, num_comments, created_utc, created_date, url
        - keyword, subreddit
        """
        raise NotImplementedError


class PrawRedditClient(BaseRedditClient):
    """
    PRAW-backed Reddit client.
    
    Advantages: Higher rate limits (~60/min), access to comments, better pagination
    Requirements: Reddit API credentials + PRAW package
    """

    def __init__(self, reddit: "praw.Reddit"):
        """Initialize with authenticated PRAW Reddit instance."""
        self.reddit = reddit

    def search_mentions(self, subreddit: str, keyword: str, start_ts: int, end_ts: int,
                       comment_limit: int = 10, max_posts: int = 100) -> List[Dict]:
        """
        Search for posts and top comments using PRAW's authenticated API.
        Uses subreddit.search() with time_filter="all", then filters by launch window.
        """
        mentions: List[Dict] = []
        sr = self.reddit.subreddit(subreddit)

        for submission in sr.search(keyword, limit=max_posts, time_filter="all"):
            # Reddit search doesn't support precise date filtering
            if not (start_ts <= submission.created_utc <= end_ts):
                continue

            # Post mention
            mentions.append({
                "type": "post",
                "title": submission.title,
                "text": submission.selftext,
                "score": submission.score,
                "num_comments": submission.num_comments,
                "created_utc": submission.created_utc,
                "created_date": datetime.fromtimestamp(submission.created_utc).strftime("%Y-%m-%d"),
                "url": f"https://reddit.com{submission.permalink}",
                "keyword": keyword,
                "subreddit": subreddit
            })

            # Top comments
            submission.comments.replace_more(limit=0)
            for comment in submission.comments.list()[:comment_limit]:
                if not (start_ts <= comment.created_utc <= end_ts):
                    continue

                mentions.append({
                    "type": "comment",
                    "title": submission.title,
                    "text": comment.body,
                    "score": comment.score,
                    "num_comments": 0,
                    "created_utc": comment.created_utc,
                    "created_date": datetime.fromtimestamp(comment.created_utc).strftime("%Y-%m-%d"),
                    "url": f"https://reddit.com{comment.permalink}",
                    "keyword": keyword,
                    "subreddit": subreddit
                })

        return mentions


class PublicRedditClient(BaseRedditClient):
    """
    Public JSON endpoint client (no authentication).
    
    Advantages: Works without credentials, quick start for testing
    Limitations: Lower rate limits (~30/min), posts only (no comments), less reliable pagination
    
    Use for: Testing, one-off analysis, small feature sets (<10)
    Avoid for: Many features (>20), comment-level sentiment, time-sensitive analysis
    """

    BASE_URL = "https://www.reddit.com"

    def __init__(self, user_agent: str = "feature-sentiment-valid-unauth/1.0"):
        """Initialize with user agent header."""
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": user_agent})

    def _search_page(self, subreddit: str, keyword: str, after: Optional[str] = None,
                    sort: str = "new", time_filter: str = "all", limit: int = 50) -> Dict:
        """
        Fetch single search page from Reddit's public JSON API with basic backoff.
        Retries on 429 with exponential backoff (2s, 5s, 10s).
        """
        url = f"{self.BASE_URL}/r/{subreddit}/search.json"
        params = {
            "q": keyword,
            "restrict_sr": "on",
            "sort": sort,
            "t": time_filter,
            "limit": limit
        }
        if after:
            params["after"] = after

        # Exponential backoff for rate limiting
        backoff_seconds = [2, 5, 10]
        for attempt, delay in enumerate(backoff_seconds, start=1):
            resp = self.session.get(url, params=params, timeout=20)
            if resp.status_code == 429:
                print(f"  ⏳ 429 for '{keyword}' (attempt {attempt}) - sleeping {delay}s")
                time.sleep(delay)
                continue

            resp.raise_for_status()
            return resp.json().get("data", {})

        # Final attempt
        resp = self.session.get(url, params=params, timeout=20)
        resp.raise_for_status()
        return resp.json().get("data", {})

    def search_mentions(self, subreddit: str, keyword: str, start_ts: int, end_ts: int,
                       comment_limit: int = 10, max_posts: int = 100) -> List[Dict]:
        """
        Search for posts using public JSON endpoint.
        
        Note: This client does not fetch comments. All mentions are post-level only.
        comment_limit is ignored (kept for interface compatibility).
        """
        mentions: List[Dict] = []
        after: Optional[str] = None

        while len(mentions) < max_posts:
            data = self._search_page(subreddit=subreddit, keyword=keyword, after=after,
                                    sort="new", time_filter="all", limit=50)
            children = data.get("children", [])
            if not children:
                break

            for item in children:
                d = item.get("data", {})
                created_utc = d.get("created_utc")
                if created_utc is None:
                    continue

                if not (start_ts <= created_utc <= end_ts):
                    continue

                mentions.append({
                    "type": "post",
                    "title": d.get("title", ""),
                    "text": d.get("selftext", ""),
                    "score": d.get("score", 0),
                    "num_comments": d.get("num_comments", 0),
                    "created_utc": created_utc,
                    "created_date": datetime.fromtimestamp(created_utc).strftime("%Y-%m-%d"),
                    "url": self.BASE_URL + d.get("permalink", ""),
                    "keyword": keyword,
                    "subreddit": subreddit
                })

                if len(mentions) >= max_posts:
                    break

            # Next page
            after = data.get("after")
            if not after:
                break

            time.sleep(1.0)  # Be gentle with public endpoints

        return mentions
