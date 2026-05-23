# Blinq Ambassador Engagement Tracking — Options

## Requirement

Track real Twitter engagement (likes, retweets, replies, views from all of Twitter) on tweets posted by 30–50 whitelisted Blinq ambassadors that include `#Blinq`. Admin needs a per-ambassador breakdown sortable by total engagement.

---

## Option 1 — TrackMyHashtag (Zero-code SaaS)

**What it does:** Monitors the `#Blinq` hashtag in real-time and shows a per-contributor breakdown — tweet count, likes, retweets, replies, reach — with date range filters.

**Setup:**
1. Sign up at trackmyhashtag.com
2. Create a tracking campaign for `#Blinq`
3. Admin logs into dashboard, filters by date range, looks up ambassador handles

**Cost:** $49/month

**Pros:**
- Zero code, zero maintenance
- Real Twitter-wide engagement metrics
- Date range filtering built-in
- Visual dashboard

**Cons:**
- Tracks everyone who uses `#Blinq`, not just whitelisted ambassadors — admin must manually focus on enrolled handles
- No whitelist/access control
- Ongoing monthly cost even when not actively reviewing

---

## Option 2 — twitterapi.io + Script (Recommended)

**What it does:** A Python script reads a list of ambassador Twitter handles, searches each one's `#Blinq` tweets via the twitterapi.io API within a given date range, and outputs a sorted leaderboard table (optionally as CSV).

**Setup:**
1. Sign up at twitterapi.io, get API key (~$0.1 free credit on signup, no card needed)
2. Create `ambassadors.txt` with whitelisted handles
3. Admin runs: `python track_engagement.py --from 2026-05-01 --to 2026-05-23`

**Cost:** ~$1–2/month for 30–50 ambassadors posting a few tweets/week

**Pros:**
- Real Twitter-wide engagement (likes, retweets, replies, views)
- Whitelist enforced — only tracks handles in the config file
- Run on demand, no server or hosting needed
- Extremely cheap
- Full control — output as table or CSV, customize as needed
- One-time write, minimal maintenance

**Cons:**
- Requires Python installed on admin's machine
- API key must be set as environment variable
- Manual run (not automated unless scheduled)

**See:** `track_engagement.py` and `ambassadors.txt` in this repo.

---

## Option 3 — Engages.io + TrackMyHashtag (Combined)

**What it does:** Use Engages.io for the Discord layer (ambassador onboarding, community quests, rewards) and TrackMyHashtag separately for real per-ambassador engagement metrics.

**Setup:**
1. Add Engage Bot to Discord, run `/setup`
2. Ambassadors connect Twitter via `/twitter` command in Discord
3. Configure `#Blinq` hashtag campaign in Engages.io (community rewards)
4. Sign up for TrackMyHashtag ($49/mo) for admin engagement reporting

**Cost:** Engages.io (plan unknown) + $49/month TrackMyHashtag

**Pros:**
- Best of both worlds: Discord onboarding/gamification + real metrics
- Community gets rewarded for engaging with ambassador tweets
- Admin has a proper analytics dashboard

**Cons:**
- Two platforms to manage
- Higher cost
- Whitelist gap still exists in TrackMyHashtag (same as Option 1)
- Engages.io plan cost unknown — may add significant cost

---

## Comparison

| | No-code | Real Twitter metrics | Whitelist enforced | Approx. cost |
|---|:---:|:---:|:---:|---|
| TrackMyHashtag | ✅ | ✅ | ❌ | $49/mo |
| twitterapi.io script | Minimal | ✅ | ✅ | ~$1–2/mo |
| Engages.io + TrackMyHashtag | ✅ | ✅ | Partial | $49/mo + |

**Recommended:** Option 2 for lowest cost and full whitelist control. Option 1 if zero code is a hard requirement.
