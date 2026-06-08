# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A POC for tracking Twitter/X engagement by whitelisted Blinq ambassadors. Ambassadors must include `#predictonblinq` in product-related tweets. The main tool is a Python script that queries the twitterapi.io API and outputs a ranked leaderboard.

## Running the Script

```bash
export TWITTERAPI_KEY=your_api_key_here
python track_engagement.py --from 2026-05-01 --to 2026-05-23
python track_engagement.py --from 2026-05-01 --to 2026-05-23 --csv my_results.csv
```

Optional flags:
- `--csv FILE` — CSV filename saved under `outputs/`; auto-generated with date+timestamp if omitted
- `--config FILE` — use a different ambassadors JSON file (default: `ambassadors_handles.json`)

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
