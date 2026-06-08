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

Fetches all tweets matching the hashtag in one pass, then attributes only those
from whitelisted ambassadors. Hashtag and ambassador list are read from ambassadors_handles.json.
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
from pathlib import Path

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
    lang: str
    source: str
    likes: int
    retweets: int
    replies: int
    views: int
    quotes: int
    bookmarks: int
    is_reply: bool
    in_reply_to_id: str
    in_reply_to_username: str
    conversation_id: str
    hashtags: list
    mentions: list
    # author fields
    author_handle: str
    author_name: str
    author_followers: int
    author_following: int
    author_verified: bool
    author_tweet_count: int
    author_created_at: str
    author_bio: str
    author_location: str

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


def to_unix(date_str: str) -> int:
    return int(datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp())


def to_iso(date_str: str, end_of_day: bool = False) -> str:
    dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    if end_of_day:
        dt = dt.replace(hour=23, minute=59, second=59)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


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


def _parse_twitterapi_tweet(t: dict) -> Tweet:
    author = t.get("author", {})
    entities = t.get("entities", {})
    hashtags = [h.get("text", "") for h in entities.get("hashtags", [])]
    mentions = [{"handle": m.get("screen_name", ""), "name": m.get("name", "")} for m in entities.get("user_mentions", [])]
    bio = author.get("profile_bio", {}).get("description", "") or author.get("description", "")
    return Tweet(
        tweet_id=t.get("id", ""),
        url=t.get("url", ""),
        text=t.get("text", ""),
        created_at=t.get("createdAt", ""),
        lang=t.get("lang", ""),
        source=t.get("source", ""),
        likes=t.get("likeCount", 0),
        retweets=t.get("retweetCount", 0),
        replies=t.get("replyCount", 0),
        views=t.get("viewCount", 0),
        quotes=t.get("quoteCount", 0),
        bookmarks=t.get("bookmarkCount", 0),
        is_reply=t.get("isReply", False),
        in_reply_to_id=t.get("inReplyToId", "") or "",
        in_reply_to_username=t.get("inReplyToUsername", "") or "",
        conversation_id=t.get("conversationId", "") or "",
        hashtags=hashtags,
        mentions=mentions,
        author_handle=author.get("userName", ""),
        author_name=author.get("name", ""),
        author_followers=author.get("followers", 0),
        author_following=author.get("following", 0),
        author_verified=author.get("isBlueVerified", False),
        author_tweet_count=author.get("statusesCount", 0),
        author_created_at=author.get("createdAt", ""),
        author_bio=bio,
        author_location=author.get("location", ""),
    )


def _twitterapi_paginate(query: str, api_key: str) -> list[dict]:
    headers = {"X-API-Key": api_key}
    results = []
    cursor = ""
    page = 1

    while True:
        params = {"query": query, "queryType": "Latest", "cursor": cursor}
        for attempt in range(5):
            try:
                resp = requests.get(TWITTERAPI_URL, headers=headers, params=params, timeout=30)
                if resp.status_code == 429:
                    wait = 10 * (attempt + 1)
                    print(f"    Rate limited, waiting {wait}s...")
                    time.sleep(wait)
                    continue
                resp.raise_for_status()
                break
            except requests.RequestException as e:
                print(f"    Warning: API error: {e}")
                return results
        else:
            print("    Warning: gave up after retries")
            break

        data = resp.json()
        batch = data.get("tweets", [])
        results.extend(batch)
        print(f"    Page {page}: {len(batch)} tweets (total so far: {len(results)})")
        page += 1

        if not data.get("has_next_page"):
            break
        cursor = data.get("next_cursor", "")
        time.sleep(0.3)

    return results


def fetch_by_hashtag(hashtag: str, since_ts: int, until_ts: int, api_key: str, allowed_handles: set[str] | None = None) -> tuple[dict[str, list[Tweet]], list[tuple[str, Tweet]]]:
    """Fetch all tweets for the hashtag, paginating fully.

    If allowed_handles is provided, only those handles are included in buckets
    (used for the ambassador leaderboard). If None, all authors are included.
    """
    query = f"{hashtag} since_time:{since_ts} until_time:{until_ts}"
    print(f"  Query: {query}")
    raw_tweets = _twitterapi_paginate(query, api_key)

    buckets: dict[str, list[Tweet]] = {}
    all_tweets: list[tuple[str, Tweet]] = []

    for t in raw_tweets:
        author = t.get("author", {}).get("userName", "").lower()
        tweet = _parse_twitterapi_tweet(t)
        all_tweets.append((author, tweet))
        if allowed_handles is None or author in allowed_handles:
            buckets.setdefault(author, []).append(tweet)

    return buckets, all_tweets


def fetch_by_hashtag_xapi(hashtag: str, from_date: str, to_date: str, bearer_token: str, allowed_handles: set[str]) -> dict[str, list[Tweet]]:
    """Fetch all hashtag tweets via X API v2, bucket by whitelisted handle."""
    query = f"{hashtag} -is:retweet"
    headers = {"Authorization": f"Bearer {bearer_token}"}
    params = {
        "query": query,
        "max_results": 100,
        "start_time": to_iso(from_date),
        "end_time": to_iso(to_date, end_of_day=True),
        "tweet.fields": "public_metrics,created_at,author_id",
        "expansions": "author_id",
        "user.fields": "username",
    }

    buckets: dict[str, list[Tweet]] = {h: [] for h in allowed_handles}
    skipped = 0

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
            print(f"    Warning: X API error: {e}")
            break

        data = resp.json()
        user_map = {u["id"]: u["username"].lower() for u in data.get("includes", {}).get("users", [])}

        for t in data.get("data", []):
            m = t.get("public_metrics", {})
            author_handle = user_map.get(t.get("author_id", ""), "")
            tweet_id = t.get("id", "")
            if author_handle in allowed_handles:
                buckets[author_handle].append(Tweet(
                    tweet_id=tweet_id,
                    url=f"https://x.com/{author_handle}/status/{tweet_id}",
                    text=t.get("text", "")[:100],
                    created_at=t.get("created_at", ""),
                    likes=m.get("like_count", 0),
                    retweets=m.get("retweet_count", 0),
                    replies=m.get("reply_count", 0),
                    views=m.get("impression_count", 0),
                    quotes=m.get("quote_count", 0),
                ))
            else:
                skipped += 1

        next_token = data.get("meta", {}).get("next_token")
        if not next_token:
            break
        params["next_token"] = next_token
        time.sleep(1)

    if skipped:
        print(f"  Skipped {skipped} tweet(s) from non-ambassadors")
    return buckets


def print_all_tweets(all_tweets: list[tuple[str, Tweet]], hashtag: str, date_from: str, date_to: str):
    print(f"\nAll tweets for {hashtag} — {date_from} to {date_to}")
    print(f"Total: {len(all_tweets)} tweet(s)\n")
    for i, (author, t) in enumerate(all_tweets, 1):
        print(f"[{i}] @{author}  •  {t.created_at}")
        print(f"    {t.text}")
        print(f"    Likes: {t.likes}  RTs: {t.retweets}  Replies: {t.replies}  Quotes: {t.quotes}  Views: {t.views}")
        print(f"    {t.url}")
        print()


def print_leaderboard(stats: list[AmbassadorStats], hashtag: str, date_from: str, date_to: str):
    print(f"\nBlinq Engagement Leaderboard — {date_from} to {date_to}")
    print(f"Hashtag: {hashtag} | {len(stats)} accounts\n")

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


def write_csvs(all_tweets: list[tuple[str, Tweet]], output_dir: Path, timestamp: str):
    tweets_path = output_dir / f"tweets_{timestamp}.csv"
    mentions_path = output_dir / f"mentions_{timestamp}.csv"

    tweet_headers = [
        "tweet_id", "url", "text", "created_at", "lang", "source",
        "likes", "retweets", "replies", "quotes", "views", "bookmarks",
        "is_reply", "in_reply_to_id", "in_reply_to_username", "conversation_id", "hashtags",
        "author_handle", "author_name", "author_followers", "author_following",
        "author_verified", "author_tweet_count", "author_created_at", "author_bio", "author_location",
    ]
    mention_headers = ["mention_handle", "mention_name", "tweet_ids", "mention_count"]

    # collect mentions: handle -> {name, tweet_ids}
    mention_map: dict[str, dict] = {}

    with open(tweets_path, "w", newline="", encoding="utf-8") as tf:
        tw = csv.writer(tf)
        tw.writerow(tweet_headers)
        for _, t in all_tweets:
            tw.writerow([
                t.tweet_id, t.url, t.text, t.created_at, t.lang, t.source,
                t.likes, t.retweets, t.replies, t.quotes, t.views, t.bookmarks,
                t.is_reply, t.in_reply_to_id, t.in_reply_to_username, t.conversation_id,
                ",".join(t.hashtags),
                t.author_handle, t.author_name, t.author_followers, t.author_following,
                t.author_verified, t.author_tweet_count, t.author_created_at, t.author_bio, t.author_location,
            ])
            for m in t.mentions:
                h = m["handle"].lower()
                if h not in mention_map:
                    mention_map[h] = {"name": m["name"], "tweet_ids": []}
                mention_map[h]["tweet_ids"].append(t.tweet_id)

    with open(mentions_path, "w", newline="", encoding="utf-8") as mf:
        mw = csv.writer(mf)
        mw.writerow(mention_headers)
        for handle, info in sorted(mention_map.items()):
            mw.writerow([handle, info["name"], ",".join(info["tweet_ids"]), len(info["tweet_ids"])])

    print(f"Tweets CSV  → {tweets_path}")
    print(f"Mentions CSV → {mentions_path}")


def main():
    parser = argparse.ArgumentParser(description="Track branded tweet engagement per ambassador")
    parser.add_argument("--from", dest="from_date", required=True, metavar="YYYY-MM-DD", help="Start date (inclusive)")
    parser.add_argument("--to", dest="to_date", required=True, metavar="YYYY-MM-DD", help="End date (inclusive)")
    parser.add_argument("--config", default=DEFAULT_AMBASSADORS_FILE, metavar="FILE",
                        help=f"Ambassadors config JSON (default: {DEFAULT_AMBASSADORS_FILE})")
    parser.add_argument("--provider", choices=["twitterapi", "xapi"], default="twitterapi",
                        help="Data source: twitterapi (default, any date range) or xapi (official X API, last 7 days on Free/Basic)")
    parser.add_argument("--all", dest="show_all", action="store_true",
                        help="List all tweets for the hashtag, ignoring the ambassador whitelist")
    args = parser.parse_args()

    since_ts = to_unix(args.from_date)
    until_ts = int(datetime.strptime(args.to_date, "%Y-%m-%d").replace(tzinfo=timezone.utc).replace(hour=23, minute=59, second=59).timestamp())
    hashtag, handles, url_map = load_config(args.config)
    allowed_handles = {h.lower() for h in handles}

    if args.provider == "xapi":
        bearer_token = os.environ.get("X_BEARER_TOKEN")
        if not bearer_token:
            raise SystemExit("Error: set X_BEARER_TOKEN in your .env file for --provider xapi.")
        print(f"Fetching {hashtag} tweets via X API ({args.from_date} → {args.to_date})...")
        buckets = fetch_by_hashtag_xapi(hashtag, args.from_date, args.to_date, bearer_token, allowed_handles)
    else:
        api_key = os.environ.get("TWITTERAPI_KEY")
        if not api_key:
            raise SystemExit("Error: set TWITTERAPI_KEY in your .env file.")
        print(f"Fetching {hashtag} tweets via twitterapi.io ({args.from_date} → {args.to_date})...")
        buckets, all_tweets = fetch_by_hashtag(hashtag, since_ts, until_ts, api_key)

    if args.show_all:
        print_all_tweets(all_tweets, hashtag, args.from_date, args.to_date)
        return

    # Build leaderboard from all handles found in results; mark ambassadors
    all_stats = []
    for handle, tweets in buckets.items():
        all_stats.append(AmbassadorStats(
            handle=handle,
            profile_url=url_map.get(handle, f"https://x.com/{handle}"),
            tweets=tweets,
        ))

    all_stats.sort(key=lambda s: s.total_engagement, reverse=True)
    print_leaderboard(all_stats, hashtag, args.from_date, args.to_date)

    output_dir = Path("outputs")
    output_dir.mkdir(exist_ok=True)
    timestamp = f"{args.from_date}_to_{args.to_date}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    write_csvs(all_tweets, output_dir, timestamp)


if __name__ == "__main__":
    main()
