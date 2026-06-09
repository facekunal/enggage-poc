# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A POC for tracking Twitter/X engagement by whitelisted Blinq ambassadors. Ambassadors must include `#predictonblinq` in product-related tweets. The main tool is a Python script that queries the twitterapi.io API and outputs a ranked leaderboard.

## Running the Script

```bash
export TWITTERAPI_KEY=your_api_key_here

# Hashtag search (twitterapi.io — default)
uv run track_engagement.py --from 2026-05-01 --to 2026-05-23 --mode hashtag

# Per-ambassador search
uv run track_engagement.py --from 2026-05-01 --to 2026-05-23 --mode per-ambassador

# From-CSV: fetch metrics for tweet URLs listed in a Discord-exported CSV
uv run track_engagement.py --mode from-csv --input-csv "discord_chat - tweets.csv"
```

Optional flags:
- `--input-csv FILE` — CSV of tweet URLs (required for `--mode from-csv`); see format below
- `--config FILE` — use a different ambassadors JSON file (default: `ambassadors_handles.json`)
- `--from`/`--to` — date range (required for `hashtag`/`per-ambassador`; optional for `from-csv`, inferred from tweet timestamps if omitted)

### `from-csv` input format

A Discord message-export CSV with columns: `Date`, `Username`, `User tag`, `Content`.
The `Content` column must contain an `x.com` or `twitter.com` status URL. Example:

```
Date,Username,User tag,Content
"2026-05-30,03:48:59",papabakouu,#0,https://x.com/i/status/2059192303726866731
"2026-05-30,06:09:05",razzshares,#0,https://x.com/razzshares/status/2059142667641278921?s=46
```

The Discord `Username` is ignored — the leaderboard uses the real Twitter handle returned by the API.

## Architecture

**`track_engagement.py`** — single-file script, no framework, no server. Key flow:
1. Loads `ambassadors_handles.json` (hashtag + ambassador handles)
2. For each handle, calls `twitterapi.io/twitter/tweet/advanced_search` with query `from:<handle> <hashtag> since_time:<ts> until_time:<ts>`
3. Paginates via `has_next_page` / `next_cursor`, 0.3s sleep between pages
4. Aggregates into `AmbassadorStats` dataclasses, sorts by `total_engagement` (likes + retweets + replies + quotes)
5. Prints a formatted table; optionally writes CSV

**`ambassadors_handles.json`** — config file. Two fields: `hashtag` (string) and `ambassadors` (list of `@handle` strings). Add/remove ambassadors here — no code changes needed.

## External Dependencies

- `requests` — only third-party dependency (`pip install requests`)
- twitterapi.io API key — set as `TWITTERAPI_KEY` env var; sign up at twitterapi.io (~$0.1 free credit, no card needed)

## Key Design Decisions

- `engagement` score excludes `views` (views are shown separately but not counted in ranking total)
- Handles in the JSON may include or omit the `@` prefix — the script strips it with `lstrip("@")`
- Date range is end-inclusive: `--to` date is converted to midnight UTC of that day, so tweets on that day are included only if posted before 00:00 UTC
