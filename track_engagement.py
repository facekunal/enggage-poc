#!/usr/bin/env python3
"""
track_engagement.py — Track branded tweet engagement per whitelisted ambassador.

Usage:
    cp .env.example .env          # add your API key(s)

    # Hashtag search (twitterapi.io — default)
    uv run track_engagement.py --from 2026-05-01 --to 2026-05-23 --mode hashtag
    uv run track_engagement.py --from 2026-05-01 --to 2026-05-23 --mode hashtag --ambassadors-only

    # Hashtag search (official X API v2)
    uv run track_engagement.py --from 2026-05-01 --to 2026-05-23 --mode hashtag --provider xapi
    uv run track_engagement.py --from 2026-05-01 --to 2026-05-23 --mode hashtag --provider xapi --ambassadors-only

    # Per-ambassador search (twitterapi.io — default)
    uv run track_engagement.py --from 2026-05-01 --to 2026-05-23 --mode per-ambassador

    # Per-ambassador search (official X API v2)
    uv run track_engagement.py --from 2026-05-01 --to 2026-05-23 --mode per-ambassador --provider xapi

Modes:
    hashtag        (default) One hashtag search. Shows all matching tweets by default;
                   add --ambassadors-only to restrict the leaderboard to whitelisted handles.
    per-ambassador One `from:<handle> <hashtag>` query per ambassador. More API calls but
                   guarantees complete per-person coverage regardless of hashtag search limits.

Providers:
    twitterapi  (default) — twitterapi.io, requires TWITTERAPI_KEY, supports any date range
    xapi        — Official X API v2, requires X_BEARER_TOKEN, last 7 days on Free/Basic plan
"""

import argparse
import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from enggage.core import DEFAULT_AMBASSADORS_FILE, build_leaderboard, load_config, to_unix, to_unix_end_of_day
from enggage.output import print_all_tweets, print_leaderboard, write_csvs
from enggage.providers import twitterapi, xapi

load_dotenv()


def mode_hashtag(args, hashtag, handles, url_map, since_ts, until_ts):
    allowed = {h.lower() for h in handles} if args.ambassadors_only else None

    if args.provider == "xapi":
        bearer_token = os.environ.get("X_BEARER_TOKEN")
        if not bearer_token:
            raise SystemExit("Error: set X_BEARER_TOKEN in your .env file for --provider xapi.")
        print(f"[hashtag / xapi] Fetching {hashtag} ({args.from_date} → {args.to_date})...")
        buckets, all_tweets = xapi.fetch_by_hashtag(hashtag, args.from_date, args.to_date, bearer_token, allowed)
    else:
        api_key = os.environ.get("TWITTERAPI_KEY")
        if not api_key:
            raise SystemExit("Error: set TWITTERAPI_KEY in your .env file.")
        print(f"[hashtag / twitterapi] Fetching {hashtag} ({args.from_date} → {args.to_date})...")
        buckets, all_tweets = twitterapi.fetch_by_hashtag(hashtag, since_ts, until_ts, api_key, allowed)

    if not args.ambassadors_only:
        print_all_tweets(all_tweets, hashtag, args.from_date, args.to_date)

    stats = build_leaderboard(buckets, url_map)
    print_leaderboard(stats, hashtag, args.from_date, args.to_date)
    return all_tweets


def mode_per_ambassador(args, hashtag, handles, url_map, since_ts, until_ts):
    if args.provider == "xapi":
        bearer_token = os.environ.get("X_BEARER_TOKEN")
        if not bearer_token:
            raise SystemExit("Error: set X_BEARER_TOKEN in your .env file for --provider xapi.")
        print(f"[per-ambassador / xapi] Fetching {hashtag} for {len(handles)} ambassadors ({args.from_date} → {args.to_date})...")
        buckets, all_tweets = xapi.fetch_per_ambassador(handles, hashtag, args.from_date, args.to_date, bearer_token)
    else:
        api_key = os.environ.get("TWITTERAPI_KEY")
        if not api_key:
            raise SystemExit("Error: set TWITTERAPI_KEY in your .env file.")
        print(f"[per-ambassador / twitterapi] Fetching {hashtag} for {len(handles)} ambassadors ({args.from_date} → {args.to_date})...")
        buckets, all_tweets = twitterapi.fetch_per_ambassador(handles, hashtag, since_ts, until_ts, api_key)

    stats = build_leaderboard(buckets, url_map)
    print_leaderboard(stats, hashtag, args.from_date, args.to_date)
    return all_tweets


def _resolve_date_range(args, all_tweets: list) -> tuple[str, str]:
    if args.from_date and args.to_date:
        return args.from_date, args.to_date
    if not all_tweets:
        today = datetime.now().strftime("%Y-%m-%d")
        return today, today
    dates = []
    for _, tweet in all_tweets:
        try:
            dt = datetime.strptime(tweet.created_at, "%a %b %d %H:%M:%S %z %Y")
            dates.append(dt.strftime("%Y-%m-%d"))
        except (ValueError, TypeError):
            pass
    if not dates:
        today = datetime.now().strftime("%Y-%m-%d")
        return today, today
    return min(dates), max(dates)


def mode_from_csv(args, hashtag, handles, url_map):
    api_key = os.environ.get("TWITTERAPI_KEY")
    if not api_key:
        raise SystemExit("Error: set TWITTERAPI_KEY in your .env file.")
    if args.provider != "twitterapi":
        print("  Note: --provider is ignored for --mode from-csv (always uses twitterapi.io)")
    print(f"[from-csv / twitterapi] Reading {args.input_csv}...")
    buckets, all_tweets, discord_names = twitterapi.fetch_from_csv(args.input_csv, api_key)
    date_from, date_to = _resolve_date_range(args, all_tweets)
    stats = build_leaderboard(buckets, url_map)
    print_leaderboard(stats, hashtag, date_from, date_to)
    return all_tweets, discord_names


def main():
    parser = argparse.ArgumentParser(description="Track branded tweet engagement per ambassador")
    parser.add_argument("--from", dest="from_date", default=None, metavar="YYYY-MM-DD",
                        help="Start date (required for hashtag/per-ambassador modes)")
    parser.add_argument("--to", dest="to_date", default=None, metavar="YYYY-MM-DD",
                        help="End date (required for hashtag/per-ambassador modes)")
    parser.add_argument("--mode", choices=["hashtag", "per-ambassador", "from-csv"], default="hashtag",
                        help="hashtag: one search for the hashtag (default); per-ambassador: one query per ambassador; from-csv: fetch metrics for tweet URLs listed in a CSV")
    parser.add_argument("--ambassadors-only", action="store_true",
                        help="(hashtag mode) restrict leaderboard to whitelisted ambassadors only")
    parser.add_argument("--provider", choices=["twitterapi", "xapi"], default="twitterapi",
                        help="twitterapi (default, any date range) or xapi (last 7 days, hashtag mode only)")
    parser.add_argument("--input-csv", metavar="FILE",
                        help="CSV file with tweet URLs (required for --mode from-csv)")
    parser.add_argument("--config", default=DEFAULT_AMBASSADORS_FILE, metavar="FILE",
                        help=f"Ambassadors config JSON (default: {DEFAULT_AMBASSADORS_FILE})")
    args = parser.parse_args()

    if args.mode in ("hashtag", "per-ambassador"):
        if not args.from_date or not args.to_date:
            parser.error(f"--from and --to are required for --mode {args.mode}")
    if args.mode == "from-csv":
        if not args.input_csv:
            parser.error("--input-csv is required for --mode from-csv")
        if not Path(args.input_csv).exists():
            parser.error(f"Input CSV not found: {args.input_csv}")

    since_ts = to_unix(args.from_date) if args.from_date else None
    until_ts = to_unix_end_of_day(args.to_date) if args.to_date else None
    hashtag, handles, url_map = load_config(args.config)

    discord_names = None
    if args.mode == "hashtag":
        all_tweets = mode_hashtag(args, hashtag, handles, url_map, since_ts, until_ts)
    elif args.mode == "per-ambassador":
        all_tweets = mode_per_ambassador(args, hashtag, handles, url_map, since_ts, until_ts)
    else:
        all_tweets, discord_names = mode_from_csv(args, hashtag, handles, url_map)

    output_dir = Path("outputs")
    output_dir.mkdir(exist_ok=True)
    if args.from_date and args.to_date:
        timestamp = f"{args.from_date}_to_{args.to_date}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    else:
        timestamp = f"fromcsv_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    write_csvs(all_tweets, output_dir, timestamp, discord_names)


if __name__ == "__main__":
    main()
