# Blinq Ambassador Engagement Tracker

Track Twitter/X engagement on tweets from whitelisted Blinq ambassadors that include `#predictonblinq`.

## What It Does

Queries each ambassador's tweets via [twitterapi.io](https://twitterapi.io), aggregates likes, retweets, replies, quotes, and views, then outputs a ranked leaderboard. Results can be exported to CSV.

## Setup

**1. Install [uv](https://docs.astral.sh/uv/) (recommended) or pip**

With uv (handles dependencies automatically):
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Or with pip:
```bash
pip install requests python-dotenv
```

**2. Get a twitterapi.io API key**

Sign up at [twitterapi.io](https://twitterapi.io) — free ~$0.1 credit on signup, no card required.

**3. Set your API key**

Create a `.env` file in the project root:
```bash
echo "TWITTERAPI_KEY=your_api_key_here" > .env
```

Or export it in your shell:
```bash
export TWITTERAPI_KEY=your_api_key_here
```

## Running

With uv (recommended — no separate install step needed):
```bash
uv run track_engagement.py --from 2026-05-01 --to 2026-05-23
```

With plain Python:
```bash
python track_engagement.py --from 2026-05-01 --to 2026-05-23
```

Save results to CSV:
```bash
uv run track_engagement.py --from 2026-05-01 --to 2026-05-23 --csv results.csv
```

## Managing Ambassadors

Edit `ambassadors_handles.json` to add or remove ambassadors. No code changes needed.

```json
{
  "hashtag": "#predictonblinq",
  "ambassadors": [
    "@handle1",
    "@handle2"
  ]
}
```

Ambassadors must include `#predictonblinq` in their product-related tweets to be tracked.

## Options

| Flag | Description |
|------|-------------|
| `--from YYYY-MM-DD` | Start date (required) |
| `--to YYYY-MM-DD` | End date (required) |
| `--csv FILE` | Save leaderboard to CSV |
| `--config FILE` | Ambassadors JSON file (default: `ambassadors_handles.json`) |
