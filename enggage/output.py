"""
output.py — leaderboard printing and CSV writing.
"""

import csv
from pathlib import Path

from enggage.core import AmbassadorStats, Tweet


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

    print(f"Tweets CSV   → {tweets_path}")
    print(f"Mentions CSV → {mentions_path}")
