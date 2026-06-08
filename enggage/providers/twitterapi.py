"""
providers/twitterapi.py — twitterapi.io client.

Supports any date range. Requires TWITTERAPI_KEY env var.
"""

import time

import requests

from enggage.core import Tweet

TWITTERAPI_URL = "https://api.twitterapi.io/twitter/tweet/advanced_search"


def _parse_tweet(t: dict) -> Tweet:
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


def _paginate(query: str, api_key: str) -> list[dict]:
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


def fetch_by_hashtag(
    hashtag: str,
    since_ts: int,
    until_ts: int,
    api_key: str,
    allowed_handles: set[str] | None = None,
) -> tuple[dict[str, list[Tweet]], list[tuple[str, Tweet]]]:
    """
    One hashtag query. Returns (buckets_by_handle, all_tweets).
    If allowed_handles is set, buckets only contain those handles.
    """
    query = f"{hashtag} since_time:{since_ts} until_time:{until_ts}"
    print(f"  Query: {query}")
    raw = _paginate(query, api_key)

    buckets: dict[str, list[Tweet]] = {}
    all_tweets: list[tuple[str, Tweet]] = []

    for t in raw:
        author = t.get("author", {}).get("userName", "").lower()
        tweet = _parse_tweet(t)
        all_tweets.append((author, tweet))
        if allowed_handles is None or author in allowed_handles:
            buckets.setdefault(author, []).append(tweet)

    return buckets, all_tweets


def fetch_per_ambassador(
    handles: list[str],
    hashtag: str,
    since_ts: int,
    until_ts: int,
    api_key: str,
) -> tuple[dict[str, list[Tweet]], list[tuple[str, Tweet]]]:
    """
    One `from:<handle> <hashtag>` query per ambassador.
    Returns (buckets_by_handle, all_tweets).
    """
    buckets: dict[str, list[Tweet]] = {}
    all_tweets: list[tuple[str, Tweet]] = []

    for handle in handles:
        query = f"from:{handle} {hashtag} since_time:{since_ts} until_time:{until_ts}"
        print(f"  [{handle}] Query: {query}")
        raw = _paginate(query, api_key)
        tweets = [_parse_tweet(t) for t in raw]
        buckets[handle.lower()] = tweets
        all_tweets.extend((handle.lower(), t) for t in tweets)
        time.sleep(15)

    return buckets, all_tweets
