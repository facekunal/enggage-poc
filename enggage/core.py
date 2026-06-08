"""
core.py — data models, config loading, and date helpers.
"""

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone

DEFAULT_AMBASSADORS_FILE = "ambassadors_handles.json"


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class Tweet:
    tweet_id: str
    url: str
    text: str
    created_at: str
    lang: str = ""
    source: str = ""
    likes: int = 0
    retweets: int = 0
    replies: int = 0
    views: int = 0
    quotes: int = 0
    bookmarks: int = 0
    is_reply: bool = False
    in_reply_to_id: str = ""
    in_reply_to_username: str = ""
    conversation_id: str = ""
    hashtags: list = field(default_factory=list)
    mentions: list = field(default_factory=list)
    author_handle: str = ""
    author_name: str = ""
    author_followers: int = 0
    author_following: int = 0
    author_verified: bool = False
    author_tweet_count: int = 0
    author_created_at: str = ""
    author_bio: str = ""
    author_location: str = ""

    @property
    def engagement(self) -> int:
        return self.likes + self.retweets + self.replies + self.quotes


@dataclass
class AmbassadorStats:
    handle: str
    profile_url: str = ""
    tweets: list = field(default_factory=list)

    @property
    def tweet_count(self) -> int:
        return len(self.tweets)

    @property
    def total_likes(self) -> int:
        return sum(t.likes for t in self.tweets)

    @property
    def total_retweets(self) -> int:
        return sum(t.retweets for t in self.tweets)

    @property
    def total_replies(self) -> int:
        return sum(t.replies for t in self.tweets)

    @property
    def total_views(self) -> int:
        return sum(t.views for t in self.tweets)

    @property
    def total_engagement(self) -> int:
        return self.total_likes + self.total_retweets + self.total_replies + sum(t.quotes for t in self.tweets)


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

def load_config(path: str) -> tuple[str, list[str], dict[str, str]]:
    if not os.path.exists(path):
        raise SystemExit(f"Config file not found: {path}")
    with open(path) as f:
        config = json.load(f)
    hashtag = config.get("hashtag", "")
    raw = config.get("ambassadors", [])
    handles = []
    url_map: dict[str, str] = {}
    for e in raw:
        if isinstance(e, dict):
            handle = e["handle"].lstrip("@")
            url_map[handle.lower()] = e.get("url", f"https://x.com/{handle}")
        else:
            handle = e.lstrip("@")
            url_map[handle.lower()] = f"https://x.com/{handle}"
        handles.append(handle)
    if not hashtag:
        raise SystemExit("No 'hashtag' field found in config file.")
    if not handles:
        raise SystemExit("No ambassadors found in config file.")
    return hashtag, handles, url_map


# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------

def to_unix(date_str: str) -> int:
    return int(datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())


def to_unix_end_of_day(date_str: str) -> int:
    return int(
        datetime.strptime(date_str, "%Y-%m-%d")
        .replace(tzinfo=timezone.utc, hour=23, minute=59, second=59)
        .timestamp()
    )


def to_iso(date_str: str, end_of_day: bool = False) -> str:
    dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    if end_of_day:
        dt = dt.replace(hour=23, minute=59, second=59)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# Leaderboard builder
# ---------------------------------------------------------------------------

def build_leaderboard(
    buckets: dict[str, list[Tweet]],
    url_map: dict[str, str],
) -> list[AmbassadorStats]:
    stats = [
        AmbassadorStats(
            handle=handle,
            profile_url=url_map.get(handle, f"https://x.com/{handle}"),
            tweets=tweets,
        )
        for handle, tweets in buckets.items()
    ]
    stats.sort(key=lambda s: s.total_engagement, reverse=True)
    return stats
