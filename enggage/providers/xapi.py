"""
providers/xapi.py — Official X API v2 client.

Only supports the last 7 days on Free/Basic plans. Requires X_BEARER_TOKEN env var.
Supports both hashtag and per-ambassador modes.
"""

import time

import requests

from enggage.core import Tweet, to_iso

XAPI_SEARCH_URL = "https://api.twitter.com/2/tweets/search/recent"


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
    One `from:<handle> <hashtag>` query per ambassador.
    Returns (buckets_by_handle, all_tweets).
    """
    buckets: dict[str, list[Tweet]] = {}
    all_tweets: list[tuple[str, Tweet]] = []

    for handle in handles:
        query = f"from:{handle} {hashtag} -is:retweet"
        print(f"  [{handle}] Query: {query}")
        results = _paginate(query, from_date, to_date, bearer_token)
        buckets[handle.lower()] = [tweet for _, tweet in results]
        all_tweets.extend(results)
        time.sleep(15)

    return buckets, all_tweets
