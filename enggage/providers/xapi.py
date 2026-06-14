"""
providers/xapi.py — Official X API v2 client.

Only supports the last 7 days on Free/Basic plans. Requires X_BEARER_TOKEN env var.
Supports hashtag, per-ambassador, and from-csv modes.
"""

import csv
import re
import time

import requests

from enggage.core import Tweet, to_iso

XAPI_SEARCH_URL = "https://api.twitter.com/2/tweets/search/recent"
XAPI_USER_URL = "https://api.x.com/2/users/by/username/{username}"
XAPI_TIMELINE_URL = "https://api.x.com/2/users/{user_id}/tweets"
XAPI_TWEETS_URL = "https://api.twitter.com/2/tweets"

_TWEET_ID_RE = re.compile(r"https?://(?:www\.)?(?:x|twitter)\.com/(?:[^/]+/)?status/(\d+)")
_BATCH_SIZE = 100


def _paginate(query: str, from_date: str, to_date: str, bearer_token: str) -> list[tuple[str, Tweet]]:
    """Run a single X API v2 search query, paginating through all results.
    Returns a list of (author_handle, Tweet) tuples.
    """
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
    results = []

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
            results.append((author_handle, Tweet(
                tweet_id=tweet_id,
                url=f"https://x.com/{author_handle}/status/{tweet_id}",
                text=t.get("text", "")[:100],
                created_at=t.get("created_at", ""),
                likes=m.get("like_count", 0),
                retweets=m.get("retweet_count", 0),
                replies=m.get("reply_count", 0),
                views=m.get("impression_count", 0),
                quotes=m.get("quote_count", 0),
                author_handle=author_handle,
            )))

        next_token = data.get("meta", {}).get("next_token")
        if not next_token:
            break
        params["next_token"] = next_token
        time.sleep(1)

    return results


def _resolve_user_id(handle: str, bearer_token: str) -> str | None:
    """Resolve a Twitter username to its numeric user ID.
    Returns the ID string, or None if the user is not found.
    """
    headers = {"Authorization": f"Bearer {bearer_token}"}
    try:
        resp = requests.get(
            XAPI_USER_URL.format(username=handle),
            headers=headers,
            timeout=15,
        )
        if resp.status_code == 404:
            print(f"    Warning: user @{handle} not found")
            return None
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"    Warning: could not resolve @{handle}: {e}")
        return None

    return resp.json().get("data", {}).get("id")


def _paginate_timeline(
    handle: str,
    user_id: str,
    from_date: str,
    to_date: str,
    bearer_token: str,
) -> list[tuple[str, Tweet]]:
    """Fetch all tweets from a user's timeline in the given date range.
    Returns a list of (author_handle, Tweet) tuples.
    """
    headers = {"Authorization": f"Bearer {bearer_token}"}
    params = {
        "max_results": 100,
        "start_time": to_iso(from_date),
        "end_time": to_iso(to_date, end_of_day=True),
        "tweet.fields": "public_metrics,created_at",
        "exclude": "retweets",
    }
    results = []

    while True:
        try:
            resp = requests.get(
                XAPI_TIMELINE_URL.format(user_id=user_id),
                headers=headers,
                params=params,
                timeout=15,
            )
            if resp.status_code == 429:
                reset = int(resp.headers.get("x-rate-limit-reset", time.time() + 60))
                wait = max(reset - int(time.time()), 1)
                print(f"    Rate limited, waiting {wait}s...")
                time.sleep(wait)
                continue
            resp.raise_for_status()
        except requests.RequestException as e:
            print(f"    Warning: X API timeline error for @{handle}: {e}")
            break

        data = resp.json()
        for t in data.get("data", []):
            m = t.get("public_metrics", {})
            tweet_id = t.get("id", "")
            results.append((handle, Tweet(
                tweet_id=tweet_id,
                url=f"https://x.com/{handle}/status/{tweet_id}",
                text=t.get("text", "")[:100],
                created_at=t.get("created_at", ""),
                likes=m.get("like_count", 0),
                retweets=m.get("retweet_count", 0),
                replies=m.get("reply_count", 0),
                views=m.get("impression_count", 0),
                quotes=m.get("quote_count", 0),
                author_handle=handle,
            )))

        next_token = data.get("meta", {}).get("next_token")
        if not next_token:
            break
        params["pagination_token"] = next_token
        time.sleep(1)

    return results


def fetch_by_hashtag(
    hashtag: str,
    from_date: str,
    to_date: str,
    bearer_token: str,
    allowed_handles: set[str] | None = None,
) -> tuple[dict[str, list[Tweet]], list[tuple[str, Tweet]]]:
    """
    One hashtag query. Returns (buckets_by_handle, all_tweets).
    If allowed_handles is set, buckets only contain those handles.
    """
    if allowed_handles is not None:
        print(
            "  Note: hashtag search may miss some tweets due to index gaps. "
            "Use --mode per-ambassador with --provider xapi for complete coverage."
        )

    query = f"{hashtag} -is:retweet"
    print(f"  Query: {query}")
    all_tweets = _paginate(query, from_date, to_date, bearer_token)

    buckets: dict[str, list[Tweet]] = {}
    skipped = 0

    for author, tweet in all_tweets:
        if allowed_handles is None or author in allowed_handles:
            buckets.setdefault(author, []).append(tweet)
        else:
            skipped += 1

    if skipped:
        print(f"  Skipped {skipped} tweet(s) from non-ambassadors")
    return buckets, all_tweets


def fetch_per_ambassador(
    handles: list[str],
    hashtag: str,
    from_date: str,
    to_date: str,
    bearer_token: str,
) -> tuple[dict[str, list[Tweet]], list[tuple[str, Tweet]]]:
    """
    Fetches each ambassador's full timeline and filters for the hashtag client-side.
    Returns (buckets_by_handle, all_tweets).
    """
    buckets: dict[str, list[Tweet]] = {}
    all_tweets: list[tuple[str, Tweet]] = []
    hashtag_lower = hashtag.lower()

    for handle in handles:
        print(f"  [{handle}] Resolving user ID...")
        user_id = _resolve_user_id(handle, bearer_token)
        if user_id is None:
            buckets[handle.lower()] = []
            time.sleep(15)
            continue

        print(f"  [{handle}] Fetching timeline (user_id={user_id})...")
        timeline = _paginate_timeline(handle.lower(), user_id, from_date, to_date, bearer_token)

        matching = [(author, tweet) for author, tweet in timeline if hashtag_lower in tweet.text.lower()]
        print(f"  [{handle}] {len(matching)}/{len(timeline)} tweets contain {hashtag}")

        buckets[handle.lower()] = [tweet for _, tweet in matching]
        all_tweets.extend(matching)
        time.sleep(15)

    return buckets, all_tweets


def _fetch_tweets_batch(tweet_ids: list[str], bearer_token: str) -> list[dict]:
    """Fetch up to _BATCH_SIZE tweets by ID. Returns raw response dicts."""
    headers = {"Authorization": f"Bearer {bearer_token}"}
    params = {
        "ids": ",".join(tweet_ids),
        "tweet.fields": "public_metrics,created_at,author_id",
        "expansions": "author_id",
        "user.fields": "username",
    }

    for attempt in range(5):
        try:
            resp = requests.get(XAPI_TWEETS_URL, headers=headers, params=params, timeout=30)
            if resp.status_code == 429:
                reset = int(resp.headers.get("x-rate-limit-reset", time.time() + 60))
                wait = max(reset - int(time.time()), 1)
                print(f"    Rate limited, waiting {wait}s...")
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            print(f"    Warning: API error fetching batch: {e}")
            return {}

    print("    Warning: gave up after retries for batch")
    return {}


def fetch_from_csv(
    csv_path: str,
    bearer_token: str,
) -> tuple[dict[str, list[Tweet]], list[tuple[str, Tweet]], dict[str, str]]:
    """Read tweet URLs from a Discord-exported CSV, fetch metrics via the X API v2
    tweet lookup endpoint, and return (buckets_by_twitter_handle, all_tweets,
    discord_name_map{tweet_id -> discord_username}).

    Expected CSV columns: Date, Username, User tag, Content
    The Content column must contain an x.com/twitter.com status URL.
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
            m = _TWEET_ID_RE.search(url)
            if m is None:
                print(f"  Warning: could not extract tweet ID from: {url!r}")
                continue
            tweet_id = m.group(1)
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
        data = _fetch_tweets_batch(batch, bearer_token)

        user_map = {u["id"]: u["username"].lower() for u in data.get("includes", {}).get("users", [])}
        tweets_data = data.get("data", [])
        print(f"    Got {len(tweets_data)} tweets back")

        for t in tweets_data:
            m_obj = t.get("public_metrics", {})
            author_id = t.get("author_id", "")
            author_handle = user_map.get(author_id, "")
            tweet_id = t.get("id", "")
            tweet = Tweet(
                tweet_id=tweet_id,
                url=f"https://x.com/{author_handle}/status/{tweet_id}",
                text=t.get("text", "")[:100],
                created_at=t.get("created_at", ""),
                likes=m_obj.get("like_count", 0),
                retweets=m_obj.get("retweet_count", 0),
                replies=m_obj.get("reply_count", 0),
                views=m_obj.get("impression_count", 0),
                quotes=m_obj.get("quote_count", 0),
                author_handle=author_handle,
            )
            if not author_handle:
                print(f"    Warning: no author handle for tweet {tweet_id}, skipping")
                continue
            buckets.setdefault(author_handle, []).append(tweet)
            all_tweets.append((author_handle, tweet))

        if batch_num < len(batches):
            time.sleep(1)

    print(f"  Done. {len(all_tweets)} tweets fetched across {len(buckets)} Twitter handles.")
    return buckets, all_tweets, discord_name_map
