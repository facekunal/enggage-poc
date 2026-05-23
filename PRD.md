# Track Twitter Engagement for Blinq Ambassadors

## 1. Overview
Track Twitter engagement (likes, retweets, comments) on Blinq-related tweets posted by ambassadors. Ambassadors are onboarded via Discord and must include `#Blinq` in all product-related tweets. Engages.io is used as the platform — no custom code required.

## 2. Goals
- Track engagement on tweets containing `#Blinq` from enrolled ambassadors
- Onboard ambassadors entirely through Discord
- Give admin visibility into per-ambassador engagement over time
- Incentivize ambassadors based on engagement scores

## 3. Users
- Ambassadors / Social Media Influencers (30–50 users)
- Admin (views engagement dashboard)

## 4. Implementation: Engages.io

### One-time Admin Setup
1. Add the Engage bot to the Discord server
2. Create a Twitter/X Campaign on Engages.io targeting the `#Blinq` hashtag
3. Configure point values for likes, retweets, and comments

### Ambassador Onboarding
1. Ambassador joins the Discord server
2. Ambassador connects their Twitter account via the Engage bot command
3. They are now enrolled — all `#Blinq` tweets will be tracked automatically

### Ongoing Flow
- Ambassador tweets about Blinq with `#Blinq` in the tweet
- Engages.io auto-tracks engagement (likes, retweets, comments) on those tweets
- Admin views the Engages.io dashboard for per-ambassador engagement leaderboard (weekly / bi-weekly / monthly views)
- Admin uses engagement scores to incentivize ambassadors via Engage's built-in points → rewards system (raffles, auctions, marketplace)

## 5. Ambassador Rule
Every product-related tweet must include `#Blinq`. Tweets without this hashtag will not be tracked.

## 6. Success Metrics
- Engagement numbers are tracked accurately per ambassador
- Admin can view engagement leaderboard and scores on Engages.io dashboard

## 7. Tradeoffs & Limitations
- Tracking is hashtag-based, not post-registration-based — relies on ambassadors consistently using `#Blinq`
- Time window for tracking is Engages.io's rolling windows (weekly/bi-weekly/monthly), not a custom 7-day per-post countdown
- Admin reporting is via Engages.io's built-in dashboard, not a custom date-range query tool

## 8. Resources
- [Engages.io](https://www.engages.io/)
- [Engage Discord Setup](https://docs.engages.io/engage-discord/setup)
- [Auto Tweet Tracking](https://docs.engages.io/new-update-and-features/auto-tweet-tracking)
- [Twitter/X Campaign Setup Guide](https://www.engages.io/guides/twitter-campaigns)
