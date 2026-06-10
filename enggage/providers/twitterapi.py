"""
providers/twitterapi.py — twitterapi.io client.

Supports any date range. Requires TWITTERAPI_KEY env var.
"""

import csv
import re
import time
from datetime import datetime

import requests

from enggage.core import Tweet

TWITTERAPI_URL = "https://api.twitterapi.io/twitter/tweet/advanced_search"
TWITTERAPI_USER_TWEETS_URL = "https://api.twitterapi.io/twitter/user/last_tweets"
TWITTERAPI_TWEETS_URL = "https://api.twitterapi.io/twitter/tweets"

_TWEET_ID_RE = re.compile(r"https?://(?:www\.)?(?:x|twitter)\.com/(?:[^/]+/)?status/(\d+)")


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


def _paginate_user_tweets(handle: str, since_ts: int, until_ts: int, api_key: str) -> list[dict]:
    """Fetch all tweets for a user in [since_ts, until_ts] via the timeline endpoint.

    The endpoint returns tweets newest-first with no server-side date filter,
    so we stop as soon as we see a tweet older than since_ts.
    """
    headers = {"X-API-Key": api_key}
    results = []
    cursor = ""
    page = 1

    while True:
        params = {"userName": handle, "cursor": cursor}
        for attempt in range(5):
            try:
                resp = requests.get(TWITTERAPI_USER_TWEETS_URL, headers=headers, params=params, timeout=30)
                if resp.status_code == 429:
                    wait = 10 * (attempt + 1)
                    print(f"    Rate limited, waiting {wait}s...")
                    time.sleep(wait)
                    continue
                resp.raise_for_status()
                break
            except requests.RequestException as e:
                print(f"    Warning: API error for @{handle}: {e}")
                return results
        else:
            print("    Warning: gave up after retries")
            break

        data = resp.json()
        batch = data.get("tweets", [])

        done = False
        for t in batch:
            created_str = t.get("createdAt", "")
            try:
                tweet_ts = int(
                    datetime.strptime(created_str, "%a %b %d %H:%M:%S %z %Y").timestamp()
                )
            except (ValueError, TypeError):
                tweet_ts = 0

            if tweet_ts > until_ts:
                continue
            if tweet_ts < since_ts:
                done = True
                break
            results.append(t)

        print(f"    Page {page}: {len(batch)} tweets, {len(results)} in range so far")
        page += 1

        if done or not data.get("has_next_page"):
            break
        cursor = data.get("next_cursor", "")
        time.sleep(0.3)

    return results


def fetch_per_ambassador(
    handles: list[str],
    hashtag: str,
    since_ts: int,
    until_ts: int,
    api_key: str,
) -> tuple[dict[str, list[Tweet]], list[tuple[str, Tweet]]]:
    """Fetches each ambassador's full timeline and filters for the hashtag client-side.
    Returns (buckets_by_handle, all_tweets).
    """
    buckets: dict[str, list[Tweet]] = {}
    all_tweets: list[tuple[str, Tweet]] = []
    hashtag_lower = hashtag.lower()

    for handle in handles:
        handle_lower = handle.lower()
        print(f"  [{handle}] Fetching timeline...")
        raw = _paginate_user_tweets(handle_lower, since_ts, until_ts, api_key)
        all_parsed = [_parse_tweet(t) for t in raw]
        matching = [t for t in all_parsed if hashtag_lower in t.text.lower()]
        print(f"  [{handle}] {len(matching)}/{len(all_parsed)} tweets contain {hashtag}")
        buckets[handle_lower] = matching
        all_tweets.extend((handle_lower, t) for t in matching)
        time.sleep(0.5)

    return buckets, all_tweets


def _extract_tweet_id(url: str) -> str | None:
    """Extract numeric tweet ID from any x.com/twitter.com status URL."""
    m = _TWEET_ID_RE.search(url.strip())
    return m.group(1) if m else None


_BATCH_SIZE = 100


def _fetch_tweets_batch(tweet_ids: list[str], api_key: str) -> list[dict]:
    """Fetch up to _BATCH_SIZE tweets by ID in one request. Returns raw tweet dicts."""
    headers = {"X-API-Key": api_key}
    params = {"tweet_ids": ",".join(tweet_ids)}

    for attempt in range(5):
        try:
            resp = requests.get(TWITTERAPI_TWEETS_URL, headers=headers, params=params, timeout=30)
            if resp.status_code == 429:
                wait = 10 * (attempt + 1)
                print(f"    Rate limited, waiting {wait}s...")
                time.sleep(wait)
                continue
            resp.raise_for_status()
            data = resp.json()
            return data.get("tweets", [])
        except requests.RequestException as e:
            print(f"    Warning: API error fetching batch: {e}")
            return []

    print("    Warning: gave up after retries for batch")
    return []


def fetch_from_csv(
    csv_path: str,
    api_key: str,
) -> tuple[dict[str, list[Tweet]], list[tuple[str, Tweet]], dict[str, str]]:
    """Read tweet URLs from a Discord-exported CSV, fetch metrics for each via
    the batch tweets endpoint, and return (buckets_by_twitter_handle, all_tweets,
    discord_name_map{tweet_id -> discord_username}).

    Expected CSV columns: Date, Username, User tag, Content
    The Content column must contain an x.com/twitter.com status URL.
    Duplicate tweet IDs are de-duplicated before any API calls.
    The bucket key is the real Twitter handle from the API response, not the
    Discord username.
    """
    tweet_ids: list[str] = []
    seen: set[str] = set()
    discord_name_map: dict[str, str] = {}

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            url = row.get("Content", "").strip()
            if not url:
                continue
            tweet_id = _extract_tweet_id(url)
            if tweet_id is None:
                print(f"  Warning: could not extract tweet ID from: {url!r}")
                continue
            if tweet_id in seen:
                continue
            seen.add(tweet_id)
            tweet_ids.append(tweet_id)
            discord_name_map[tweet_id] = row.get("Username", "").strip()

    print(f"  {len(tweet_ids)} unique tweet IDs parsed from {csv_path}")

    buckets: dict[str, list[Tweet]] = {}
    all_tweets: list[tuple[str, Tweet]] = []

    batches = [tweet_ids[i:i + _BATCH_SIZE] for i in range(0, len(tweet_ids), _BATCH_SIZE)]
    for batch_num, batch in enumerate(batches, 1):
        print(f"  Batch {batch_num}/{len(batches)}: fetching {len(batch)} tweets...")
        raw_list = _fetch_tweets_batch(batch, api_key)
        print(f"    Got {len(raw_list)} tweets back")

        for raw in raw_list:
            tweet = _parse_tweet(raw)
            handle = tweet.author_handle.lower()
            if not handle:
                print(f"    Warning: no author handle for tweet {tweet.tweet_id}, skipping")
                continue
            buckets.setdefault(handle, []).append(tweet)
            all_tweets.append((handle, tweet))

        if batch_num < len(batches):
            time.sleep(0.3)

    print(f"  Done. {len(all_tweets)} tweets fetched across {len(buckets)} Twitter handles.")
    return buckets, all_tweets, discord_name_map
