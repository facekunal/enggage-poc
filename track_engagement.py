#!/usr/bin/env python3
"""
track_engagement.py — Track branded tweet engagement per whitelisted ambassador.

Usage:
    cp .env.example .env          # add your API key(s)
    uv run track_engagement.py --from 2026-05-01 --to 2026-05-23
    uv run track_engagement.py --from 2026-05-01 --to 2026-05-23 --csv results.csv
    uv run track_engagement.py --from 2026-05-01 --to 2026-05-23 --provider xapi

Providers:
    twitterapi  (default) — twitterapi.io, requires TWITTERAPI_KEY, supports any date range
    xapi        — Official X API v2, requires X_BEARER_TOKEN, last 7 days on Free/Basic plan

Ambassadors and hashtag are read from ambassadors_handles.json.
Metrics pulled: likes, retweets, replies, views per tweet.
Output: leaderboard sorted by total engagement.
"""

import argparse
import csv
import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv

load_dotenv()

TWITTERAPI_URL = "https://api.twitterapi.io/twitter/tweet/advanced_search"
XAPI_SEARCH_URL = "https://api.twitter.com/2/tweets/search/recent"
DEFAULT_AMBASSADORS_FILE = "ambassadors_handles.json"


@dataclass
class Tweet:
    tweet_id: str
    url: str
    text: str
    created_at: str
    likes: int
    retweets: int
    replies: int
    views: int
    quotes: int

    @property
    def engagement(self) -> int:
        return self.likes + self.retweets + self.replies + self.quotes


@dataclass
class AmbassadorStats:
    handle: str
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


def to_unix(date_str: str) -> int:
    return int(datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())


def to_iso(date_str: str, end_of_day: bool = False) -> str:
    dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    if end_of_day:
        dt = dt.replace(hour=23, minute=59, second=59)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def load_config(path: str) -> tuple[str, list[str]]:
    if not os.path.exists(path):
        raise SystemExit(f"Config file not found: {path}")
    with open(path) as f:
        config = json.load(f)
    hashtag = config.get("hashtag", "")
    handles = [h.lstrip("@") for h in config.get("ambassadors", [])]
    if not hashtag:
        raise SystemExit("No 'hashtag' field found in config file.")
    if not handles:
        raise SystemExit("No ambassadors found in config file.")
    return hashtag, handles


def fetch_ambassador_tweets(handle: str, hashtag: str, since_ts: int, until_ts: int, api_key: str, no_hashtag: bool = False) -> list[Tweet]:
    """Fetch tweets via twitterapi.io."""
    tag_part = "" if no_hashtag else f" {hashtag}"
    query = f"from:{handle}{tag_part} since_time:{since_ts} until_time:{until_ts}"
    headers = {"X-API-Key": api_key}
    tweets = []
    cursor = ""

    while True:
        params = {"query": query, "queryType": "Latest", "cursor": cursor}
        for attempt in range(5):
            try:
                resp = requests.get(TWITTERAPI_URL, headers=headers, params=params, timeout=15)
                if resp.status_code == 429:
                    wait = 10 * (attempt + 1)
                    print(f"    Rate limited, waiting {wait}s...")
                    time.sleep(wait)
                    continue
                resp.raise_for_status()
                break
            except requests.RequestException as e:
                print(f"    Warning: API error for @{handle}: {e}")
                return tweets
        else:
            print(f"    Warning: gave up after retries for @{handle}")
            break

        data = resp.json()
        for t in data.get("tweets", []):
            tweets.append(Tweet(
                tweet_id=t.get("id", ""),
                url=t.get("url", ""),
                text=t.get("text", "")[:100],
                created_at=t.get("createdAt", ""),
                likes=t.get("likeCount", 0),
                retweets=t.get("retweetCount", 0),
                replies=t.get("replyCount", 0),
                views=t.get("viewCount", 0),
                quotes=t.get("quoteCount", 0),
            ))

        if not data.get("has_next_page"):
            break
        cursor = data.get("next_cursor", "")
        time.sleep(0.3)

    return tweets


def fetch_ambassador_tweets_xapi(handle: str, hashtag: str, from_date: str, to_date: str, bearer_token: str) -> list[Tweet]:
    """Fetch tweets via official X API v2 (search/recent — last 7 days on Free/Basic plans)."""
    query = f"from:{handle} {hashtag} -is:retweet"
    headers = {"Authorization": f"Bearer {bearer_token}"}
    params = {
        "query": query,
        "max_results": 100,
        "start_time": to_iso(from_date),
        "end_time": to_iso(to_date, end_of_day=True),
        "tweet.fields": "public_metrics,created_at",
        "expansions": "author_id",
    }
    tweets = []

    while True:
        try:
            resp = requests.get(XAPI_SEARCH_URL, headers=headers, params=params, timeout=15)
            if resp.status_code == 429:
                reset = int(resp.headers.get("x-rate-limit-reset", time.time() + 60))
                wait = max(reset - int(time.time()), 1)
                print(f"    Rate limited, waiting {wait}s...")
                time.sleep(wait)
                continue
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"    Warning: X API error for @{handle}: {e}")
            break

        data = resp.json()
        for t in data.get("data", []):
            m = t.get("public_metrics", {})
            tweet_id = t.get("id", "")
            tweets.append(Tweet(
                tweet_id=tweet_id,
                url=f"https://x.com/{handle}/status/{tweet_id}",
                text=t.get("text", "")[:100],
                created_at=t.get("created_at", ""),
                likes=m.get("like_count", 0),
                retweets=m.get("retweet_count", 0),
                replies=m.get("reply_count", 0),
                views=m.get("impression_count", 0),
                quotes=m.get("quote_count", 0),
            ))

        next_token = data.get("meta", {}).get("next_token")
        if not next_token:
            break
        params["next_token"] = next_token
        time.sleep(1)

    return tweets


def print_leaderboard(stats: list[AmbassadorStats], hashtag: str, date_from: str, date_to: str):
    print(f"\nBlinq Ambassador Engagement Leaderboard — {date_from} to {date_to}")
    print(f"Hashtag: {hashtag} | {len(stats)} ambassadors\n")

    header = f"{'#':<4} {'Handle':<22} {'Tweets':>6} {'Likes':>8} {'Retweets':>10} {'Replies':>8} {'Views':>10} {'Total Eng':>10}"
    print(header)
    print("-" * len(header))

    for rank, s in enumerate(stats, 1):
        print(
            f"{rank:<4} @{s.handle:<21} "
            f"{s.tweet_count:>6} {s.total_likes:>8} {s.total_retweets:>10} "
            f"{s.total_replies:>8} {s.total_views:>10} {s.total_engagement:>10}"
        )
    print()


def write_csv(stats: list[AmbassadorStats], path: str):
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["rank", "handle", "tweets", "likes", "retweets", "replies", "views", "total_engagement"])
        for rank, s in enumerate(stats, 1):
            writer.writerow([rank, s.handle, s.tweet_count, s.total_likes, s.total_retweets,
                             s.total_replies, s.total_views, s.total_engagement])
    print(f"CSV saved to {path}")


def main():
    parser = argparse.ArgumentParser(description="Track branded tweet engagement per ambassador")
    parser.add_argument("--from", dest="from_date", required=True, metavar="YYYY-MM-DD", help="Start date (inclusive)")
    parser.add_argument("--to", dest="to_date", required=True, metavar="YYYY-MM-DD", help="End date (inclusive)")
    parser.add_argument("--csv", dest="csv_path", metavar="FILE", help="Save results to CSV")
    parser.add_argument("--config", default=DEFAULT_AMBASSADORS_FILE, metavar="FILE",
                        help=f"Ambassadors config JSON (default: {DEFAULT_AMBASSADORS_FILE})")
    parser.add_argument("--provider", choices=["twitterapi", "xapi"], default="twitterapi",
                        help="Data source: twitterapi (default, any date range) or xapi (official X API, last 7 days on Free/Basic)")
    parser.add_argument("--no-hashtag", action="store_true", help="Fetch all tweets from ambassadors, ignoring the hashtag filter")
    args = parser.parse_args()

    since_ts = to_unix(args.from_date)
    until_ts = int(datetime.strptime(args.to_date, "%Y-%m-%d").replace(tzinfo=timezone.utc).replace(hour=23, minute=59, second=59).timestamp())
    hashtag, handles = load_config(args.config)

    if args.provider == "xapi":
        bearer_token = os.environ.get("X_BEARER_TOKEN")
        if not bearer_token:
            raise SystemExit("Error: set X_BEARER_TOKEN in your .env file for --provider xapi.")
        print(f"Fetching {hashtag} tweets for {len(handles)} ambassadors via X API ({args.from_date} → {args.to_date})...")
        all_stats = []
        for handle in handles:
            tweets = fetch_ambassador_tweets_xapi(handle, hashtag, args.from_date, args.to_date, bearer_token)
            all_stats.append(AmbassadorStats(handle=handle, tweets=tweets))
            status = f"{len(tweets)} tweet(s)" if tweets else "no tweets"
            print(f"  @{handle}: {status}")
    else:
        api_key = os.environ.get("TWITTERAPI_KEY")
        if not api_key:
            raise SystemExit("Error: set TWITTERAPI_KEY in your .env file.")
        print(f"Fetching {hashtag} tweets for {len(handles)} ambassadors via twitterapi.io ({args.from_date} → {args.to_date})...")
        all_stats = []
        for handle in handles:
            tweets = fetch_ambassador_tweets(handle, hashtag, since_ts, until_ts, api_key, no_hashtag=args.no_hashtag)
            all_stats.append(AmbassadorStats(handle=handle, tweets=tweets))
            status = f"{len(tweets)} tweet(s)" if tweets else "no tweets"
            print(f"  @{handle}: {status}")

    all_stats.sort(key=lambda s: s.total_engagement, reverse=True)
    print_leaderboard(all_stats, hashtag, args.from_date, args.to_date)

    if args.csv_path:
        write_csv(all_stats, args.csv_path)


if __name__ == "__main__":
    main()
