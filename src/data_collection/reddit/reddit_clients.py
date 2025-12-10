"""
Reddit API client implementations.

Provides two modes for accessing Reddit data:
1. **PRAW (authenticated)** - Preferred. Uses Reddit API credentials for higher rate limits
   and access to comments.
2. **Public JSON (fallback)** - No authentication required. Uses Reddit's public endpoints.
   More limited (posts only, no comments) but works without API keys.

Product Analyst Context:
    Rate limits are the key constraint. PRAW allows ~60 requests/minute. Public JSON is
    much more restrictive (~30 requests/minute with backoff). For analyzing 40+ features,
    authenticated access is strongly recommended to avoid multi-hour runtime.
"""

from datetime import datetime
from typing import Dict, List, Optional
import time

import requests

try:
    import praw  # Optional: only required for authenticated mode
except ImportError:
    praw = None


class BaseRedditClient:
    """
    Abstract base client defining the Reddit interface expected by RedditValidator.
    
    This interface ensures both PRAW and public JSON clients can be used interchangeably,
    allowing graceful degradation when API credentials aren't available.
    """

    def search_mentions(
        self,
        subreddit: str,
        keyword: str,
        start_ts: int,
        end_ts: int,
        comment_limit: int = 10,
        max_posts: int = 100,
    ) -> List[Dict]:
        """
        Search for mentions of a keyword in a subreddit between timestamps.

        Args:
            subreddit: Subreddit name (without 'r/' prefix).
            keyword: Search query string.
            start_ts: Start of time window (Unix timestamp).
            end_ts: End of time window (Unix timestamp).
            comment_limit: Max number of top comments to retrieve per post (if supported).
            max_posts: Max number of posts to retrieve.

        Returns:
            List of mention dictionaries with standardized schema:
                - type: "post" or "comment"
                - title: Post title
                - text: Post body or comment text
                - score: Upvote score
                - num_comments: Number of comments (posts only)
                - created_utc: Unix timestamp
                - created_date: ISO date string (YYYY-MM-DD)
                - url: Full Reddit URL
                - keyword: Search keyword that matched this result
                - subreddit: Subreddit name
        """
        raise NotImplementedError


class PrawRedditClient(BaseRedditClient):
    """
    Reddit client using PRAW (Python Reddit API Wrapper).
    
    Advantages:
        - Higher rate limits (~60 requests/minute)
        - Access to comment threads
        - More reliable pagination
        - Better error handling
        
    Requirements:
        - Reddit API credentials (client_id, client_secret, username, password)
        - PRAW package installed
    """

    def __init__(self, reddit: "praw.Reddit"):
        """
        Initialize PRAW-backed client.

        Args:
            reddit: Authenticated PRAW Reddit instance. Should be initialized with
                    credentials before passing to this client.
                    
        Example:
            ```python
            reddit = praw.Reddit(
                client_id="your_client_id",
                client_secret="your_secret",
                username="your_username",
                password="your_password",
                user_agent="feature-validator/1.0"
            )
            client = PrawRedditClient(reddit)
            ```
        """
        self.reddit = reddit

    def search_mentions(
        self,
        subreddit: str,
        keyword: str,
        start_ts: int,
        end_ts: int,
        comment_limit: int = 10,
        max_posts: int = 100,
    ) -> List[Dict]:
        """
        Search for posts and top comments using PRAW's authenticated API.
        
        Search Strategy:
            - Use subreddit.search() with time_filter="all"
            - Filter results by launch window (start_ts to end_ts)
            - For each matching post, retrieve top N comments
            - Return both posts and comments as standardized mention dicts

        Returns:
            List of mention dictionaries (posts + comments).
        """
        mentions: List[Dict] = []
        sr = self.reddit.subreddit(subreddit)

        for submission in sr.search(keyword, limit=max_posts, time_filter="all"):
            # Filter by date window - Reddit search doesn't support precise date filtering
            if not (start_ts <= submission.created_utc <= end_ts):
                continue

            # Post mention
            mentions.append(
                {
                    "type": "post",
                    "title": submission.title,
                    "text": submission.selftext,
                    "score": submission.score,
                    "num_comments": submission.num_comments,
                    "created_utc": submission.created_utc,
                    "created_date": datetime.fromtimestamp(
                        submission.created_utc
                    ).strftime("%Y-%m-%d"),
                    "url": f"https://reddit.com{submission.permalink}",
                    "keyword": keyword,
                    "subreddit": subreddit,
                }
            )

            # Top comments - expand "more comments" objects first
            submission.comments.replace_more(limit=0)
            for comment in submission.comments.list()[:comment_limit]:
                if not (start_ts <= comment.created_utc <= end_ts):
                    continue

                mentions.append(
                    {
                        "type": "comment",
                        "title": submission.title,  # Include parent post title
                        "text": comment.body,
                        "score": comment.score,
                        "num_comments": 0,  # Comments don't have sub-comments in this analysis
                        "created_utc": comment.created_utc,
                        "created_date": datetime.fromtimestamp(
                            comment.created_utc
                        ).strftime("%Y-%m-%d"),
                        "url": f"https://reddit.com{comment.permalink}",
                        "keyword": keyword,
                        "subreddit": subreddit,
                    }
                )

        return mentions


class PublicRedditClient(BaseRedditClient):
    """
    Reddit client using public JSON endpoints (no authentication required).

    Advantages:
        - Works without API credentials
        - No account setup required
        - Quick start for testing
        
    Limitations:
        - Lower rate limits (~30 requests/minute with backoff)
        - Posts only (no comments)
        - Less reliable pagination
        - May hit 429 errors more frequently
        
    Use When:
        - Testing without credentials
        - One-off analysis
        - Small feature sets (<10 features)
        
    Avoid When:
        - Analyzing many features (>20)
        - Need comment-level sentiment
        - Time-sensitive analysis
    """

    BASE_URL = "https://www.reddit.com"

    def __init__(self, user_agent: str = "feature-sentiment-valid-unauth/1.0"):
        """
        Initialize public JSON client.

        Args:
            user_agent: User agent header for HTTP requests. Reddit requires
                        a descriptive user agent string.
        """
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": user_agent})

    def _search_page(
        self,
        subreddit: str,
        keyword: str,
        after: Optional[str] = None,
        sort: str = "new",
        time_filter: str = "all",
        limit: int = 50,
    ) -> Dict:
        """
        Fetch a single search page from Reddit's public JSON API with basic backoff.
        
        Backoff Strategy:
            - On 429 (rate limit): Retry after 2s, 5s, 10s
            - On success: Return immediately
            - On final failure: Raise exception
            
        Why "new" sort:
            We sort by "new" to ensure we capture all posts in the time window,
            regardless of score. Sorting by "relevance" or "hot" might miss low-scoring
            but temporally relevant posts.

        Args:
            subreddit: Subreddit name (without 'r/' prefix).
            keyword: Search query string.
            after: Pagination token from previous page (Reddit 'after' field).
            sort: Sort mode for Reddit search (e.g., 'new', 'relevance').
            time_filter: Time filter (e.g., 'all', 'year').
            limit: Max number of posts to request for this page (max 100).

        Returns:
            Raw 'data' dict from the Reddit JSON response.
            
        Raises:
            HTTPError: If request fails after all retry attempts.
        """
        url = f"{self.BASE_URL}/r/{subreddit}/search.json"
        params = {
            "q": keyword,
            "restrict_sr": "on",  # Search only within this subreddit
            "sort": sort,
            "t": time_filter,
            "limit": limit,
        }
        if after:
            params["after"] = after

        # Basic exponential backoff for rate limiting
        backoff_seconds = [2, 5, 10]
        for attempt, delay in enumerate(backoff_seconds, start=1):
            resp = self.session.get(url, params=params, timeout=20)
            if resp.status_code == 429:
                print(
                    f"  ⏳ 429 Too Many Requests for '{keyword}' "
                    f"(attempt {attempt}) – sleeping {delay}s..."
                )
                time.sleep(delay)
                continue

            resp.raise_for_status()
            return resp.json().get("data", {})

        # Final attempt; will raise if still failing
        resp = self.session.get(url, params=params, timeout=20)
        resp.raise_for_status()
        return resp.json().get("data", {})

    def search_mentions(
        self,
        subreddit: str,
        keyword: str,
        start_ts: int,
        end_ts: int,
        comment_limit: int = 10,  # Unused, kept for interface compatibility
        max_posts: int = 100,
    ) -> List[Dict]:
        """
        Search for posts using the public JSON search endpoint.

        Note:
            This client does not fetch comments. All mentions are post-level only.
            The comment_limit parameter is kept for interface compatibility but ignored.

        Pagination:
            Reddit's JSON API uses cursor-based pagination with "after" tokens.
            We continue fetching pages until we reach max_posts or run out of results.

        Args:
            subreddit: Subreddit name (without 'r/' prefix).
            keyword: Search query string.
            start_ts: Start of time window (Unix timestamp).
            end_ts: End of time window (Unix timestamp).
            comment_limit: Ignored for public client (no comment access).
            max_posts: Max number of posts to retrieve.

        Returns:
            List of post-level mention dictionaries (no comments).
        """
        mentions: List[Dict] = []
        after: Optional[str] = None

        while len(mentions) < max_posts:
            data = self._search_page(
                subreddit=subreddit,
                keyword=keyword,
                after=after,
                sort="new",
                time_filter="all",
                limit=50,  # Max per page supported by Reddit
            )
            children = data.get("children", [])
            if not children:
                break  # No more results

            for item in children:
                d = item.get("data", {})
                created_utc = d.get("created_utc")
                if created_utc is None:
                    continue

                # Filter by time window
                if not (start_ts <= created_utc <= end_ts):
                    continue

                mentions.append(
                    {
                        "type": "post",
                        "title": d.get("title", ""),
                        "text": d.get("selftext", ""),
                        "score": d.get("score", 0),
                        "num_comments": d.get("num_comments", 0),
                        "created_utc": created_utc,
                        "created_date": datetime.fromtimestamp(
                            created_utc
                        ).strftime("%Y-%m-%d"),
                        "url": self.BASE_URL + d.get("permalink", ""),
                        "keyword": keyword,
                        "subreddit": subreddit,
                    }
                )

                if len(mentions) >= max_posts:
                    break

            # Get next page token
            after = data.get("after")
            if not after:
                break  # No more pages

            # Be gentle with public endpoints - avoid hammering the API
            time.sleep(1.0)

        return mentions