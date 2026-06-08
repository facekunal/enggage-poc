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

## Modes compared

| | `--mode hashtag` | `--mode per-ambassador` |
|---|---|---|
| API calls | 1 (+ pagination) | 1 per ambassador (+ pagination each) |
| Coverage | All accounts using the hashtag | Only whitelisted ambassadors |
| Use when | You want to see who *else* is using the hashtag | You want guaranteed complete data per ambassador |

## Options

| Flag | Description |
|------|-------------|
| `--from YYYY-MM-DD` | Start date (required) |
| `--to YYYY-MM-DD` | End date (required) |
| `--mode` | `hashtag` (default) or `per-ambassador` |
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
