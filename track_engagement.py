#!/usr/bin/env python3
"""
track_engagement.py — Track #Blinq tweet engagement per whitelisted ambassador.

Usage:
    export TWITTERAPI_KEY=your_api_key_here
    python track_engagement.py --from 2026-05-01 --to 2026-05-23
    python track_engagement.py --from 2026-05-01 --to 2026-05-23 --csv results.csv

Ambassadors are read from ambassadors.txt (one handle per line).
Metrics pulled: likes, retweets, replies, views per tweet.
Output: leaderboard sorted by total engagement.
"""

import argparse
import csv
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone

import requests

API_URL = "https://api.twitterapi.io/twitter/tweet/advanced_search"
HASHTAG = "#Blinq"
DEFAULT_AMBASSADORS_FILE = "ambassadors.txt"


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


def load_handles(path: str) -> list[str]:
    if not os.path.exists(path):
        raise SystemExit(f"Ambassadors file not found: {path}")
    handles = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                handles.append(line.lstrip("@"))
    if not handles:
        raise SystemExit(f"No ambassador handles found in {path}")
    return handles


def fetch_ambassador_tweets(handle: str, since_ts: int, until_ts: int, api_key: str) -> list[Tweet]:
    query = f"from:{handle} {HASHTAG} since_time:{since_ts} until_time:{until_ts}"
    headers = {"X-API-Key": api_key}
    tweets = []
    cursor = ""

    while True:
        params = {"query": query, "queryType": "Latest", "cursor": cursor}
        try:
            resp = requests.get(API_URL, headers=headers, params=params, timeout=15)
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"    Warning: API error for @{handle}: {e}")
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


def print_leaderboard(stats: list[AmbassadorStats], date_from: str, date_to: str):
    print(f"\nBlinq Ambassador Engagement Leaderboard — {date_from} to {date_to}")
    print(f"Hashtag: {HASHTAG} | {len(stats)} ambassadors\n")

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
    parser = argparse.ArgumentParser(description=f"Track {HASHTAG} tweet engagement per ambassador")
    parser.add_argument("--from", dest="from_date", required=True, metavar="YYYY-MM-DD", help="Start date (inclusive)")
    parser.add_argument("--to", dest="to_date", required=True, metavar="YYYY-MM-DD", help="End date (inclusive)")
    parser.add_argument("--csv", dest="csv_path", metavar="FILE", help="Save results to CSV")
    parser.add_argument("--ambassadors", default=DEFAULT_AMBASSADORS_FILE, metavar="FILE",
                        help=f"Ambassador handles file (default: {DEFAULT_AMBASSADORS_FILE})")
    args = parser.parse_args()

    api_key = os.environ.get("TWITTERAPI_KEY")
    if not api_key:
        raise SystemExit("Error: set the TWITTERAPI_KEY environment variable before running.")

    since_ts = to_unix(args.from_date)
    until_ts = to_unix(args.to_date)
    handles = load_handles(args.ambassadors)

    print(f"Fetching {HASHTAG} tweets for {len(handles)} ambassadors ({args.from_date} → {args.to_date})...")

    all_stats = []
    for handle in handles:
        tweets = fetch_ambassador_tweets(handle, since_ts, until_ts, api_key)
        all_stats.append(AmbassadorStats(handle=handle, tweets=tweets))
        status = f"{len(tweets)} tweet(s)" if tweets else "no tweets"
        print(f"  @{handle}: {status}")

    all_stats.sort(key=lambda s: s.total_engagement, reverse=True)
    print_leaderboard(all_stats, args.from_date, args.to_date)

    if args.csv_path:
        write_csv(all_stats, args.csv_path)


if __name__ == "__main__":
    main()
