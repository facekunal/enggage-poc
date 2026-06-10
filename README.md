# Blinq Ambassador Engagement Tracker

Track Twitter/X engagement on tweets from whitelisted Blinq ambassadors that include `#predictonblinq`.

## What It Does

Queries tweets via [twitterapi.io](https://twitterapi.io) or the official X API v2, aggregates likes, retweets, replies, quotes, and views, then outputs a ranked leaderboard and saves results to CSV.

## Setup

**1. Install [uv](https://docs.astral.sh/uv/) (recommended) or pip**

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Or with pip:
```bash
pip install requests python-dotenv
```

**2. Get API credentials**

- **twitterapi.io** (default) — sign up at [twitterapi.io](https://twitterapi.io), free ~$0.1 credit on signup, no card required. Supports any date range.
- **Official X API v2** (optional) — requires a Bearer Token from the [X Developer Portal](https://developer.twitter.com). Limited to the last 7 days on Free/Basic plans.

**3. Set your credentials**

```bash
# twitterapi.io (required for default provider)
echo "TWITTERAPI_KEY=your_key_here" >> .env

# Official X API v2 (only needed if using --provider xapi)
echo "X_BEARER_TOKEN=your_token_here" >> .env
```

## Running

### Mode 1 — Hashtag search

One query for the hashtag. Shows everyone who used it, or restrict to ambassadors with `--ambassadors-only`.

```bash
# twitterapi.io (any date range)
uv run track_engagement.py --from 2026-05-18 --to 2026-06-08 --mode hashtag
uv run track_engagement.py --from 2026-05-18 --to 2026-06-08 --mode hashtag --ambassadors-only

# Official X API v2 (last 7 days only)
uv run track_engagement.py --from 2026-06-01 --to 2026-06-08 --mode hashtag --provider xapi
uv run track_engagement.py --from 2026-06-01 --to 2026-06-08 --mode hashtag --provider xapi --ambassadors-only
```

### Mode 2 — Per-ambassador search

One `from:<handle> #predictonblinq` query per ambassador. More API calls, but guarantees complete per-person coverage regardless of hashtag search pagination limits.

```bash
# twitterapi.io (any date range)
uv run track_engagement.py --from 2026-05-18 --to 2026-06-08 --mode per-ambassador

# Official X API v2 (last 7 days only)
uv run track_engagement.py --from 2026-06-01 --to 2026-06-08 --mode per-ambassador --provider xapi
```

### Mode 3 — From CSV (RECOMMENDED)

Fetch metrics for a list of tweet URLs already collected (e.g. from a Discord channel export). No hashtag search or timeline traversal — just direct lookup by tweet ID.

```bash
uv run track_engagement.py --mode from-csv --input-csv "discord_chat - tweets.csv"
```

`--from` / `--to` are optional in this mode; dates are inferred from the fetched tweet timestamps.

**Input CSV format** — Discord message export with columns `Date`, `Username`, `User tag`, `Content`:

```
Date,Username,User tag,Content
"2026-05-30,03:48:59",papabakouu,#0,https://x.com/i/status/2059192303726866731
"2026-05-30,06:09:05",razzshares,#0,https://x.com/razzshares/status/2059142667641278921?s=46
```

The `Content` column must contain an `x.com` or `twitter.com` status URL. The `Username` (Discord name) is preserved in the output CSV as a `discord_name` column alongside the real Twitter handle.

### Running both flows back-to-back (last 3 weeks)

```bash
uv run track_engagement.py --from 2026-05-18 --to 2026-06-08 --mode hashtag --ambassadors-only && \
uv run track_engagement.py --from 2026-05-18 --to 2026-06-08 --mode per-ambassador
```

Each run saves its own timestamped CSVs to `outputs/`, so results won't overwrite each other.

## Providers vs Modes

|  | `--provider twitterapi` (default) | `--provider xapi` |
|---|---|---|
| **`--mode hashtag`** | ✅ any date range | ✅ last 7 days only |
| **`--mode per-ambassador`** | ✅ any date range | ✅ last 7 days only |
| **`--mode from-csv`** | ✅ always | — |

## Modes compared

| | `--mode hashtag` | `--mode per-ambassador` | `--mode from-csv` |
|---|---|---|---|
| API calls | 1 (+ pagination) | 1 per ambassador (+ pagination each) | 1 per 100 tweets |
| Coverage | All accounts using the hashtag | Only whitelisted ambassadors | Exactly the URLs in the CSV |
| Date range required | ✅ | ✅ | ❌ (inferred) |
| Use when | You want to see who *else* is using the hashtag | You want guaranteed complete data per ambassador | You have a pre-collected list of tweet URLs |

## Options

| Flag | Description |
|------|-------------|
| `--from YYYY-MM-DD` | Start date (required for `hashtag`/`per-ambassador`) |
| `--to YYYY-MM-DD` | End date (required for `hashtag`/`per-ambassador`) |
| `--mode` | `hashtag` (default), `per-ambassador`, or `from-csv` |
| `--input-csv FILE` | CSV with tweet URLs (required for `--mode from-csv`) |
| `--provider` | `twitterapi` (default, any date range) or `xapi` (last 7 days) |
| `--ambassadors-only` | Hashtag mode: restrict leaderboard to whitelisted handles only |
| `--config FILE` | Ambassadors JSON file (default: `ambassadors_handles.json`) |

## Managing Ambassadors

Edit `ambassadors_handles.json` to add or remove ambassadors. No code changes needed.

```json
{
  "hashtag": "#predictonblinq",
  "ambassadors": [
    { "handle": "@handle1", "url": "https://x.com/handle1" },
    { "handle": "@handle2", "url": "https://x.com/handle2" }
  ]
}
```

## Project Structure

```
enggage-poc/
├── track_engagement.py          # entry point
├── ambassadors_handles.json     # ambassador whitelist + hashtag config
├── enggage/
│   ├── core.py                  # data models, config loader, date helpers
│   ├── output.py                # leaderboard printing and CSV writing
│   └── providers/
│       ├── twitterapi.py        # twitterapi.io client (any date range)
│       └── xapi.py              # official X API v2 client (last 7 days)
└── outputs/                     # timestamped CSV results
```
