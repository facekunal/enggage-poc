# Track Twitter Engagement 

1. Overview
The idea is to build a system that can track Twitter post engagement (i.e. likes, re-shares, comments, and views). This program will be for investors that will bring engagement with the product and bring more users. We will manually onboard the ambassadors on discord and provide some link or something to the ambassador through which they can publish their posts (basically register their posts). Another way is to have tracking for a short period like 7 days for each post. That will be more reasonable I believe. So after this tracking period the records won't be updated. Admin should be able to look at this engagement numbers for each ambassador in a time duration. 

2. Goals
a. Each post will be tracked for a week.
b. Able to store the weekly engagement details for each tracked post.
c. user or an investor should be able to register their post so that it can be tracked in our system. 
    - Medium communication with the ambassadors will be on Discord. 
    - Decide on the process of how the ambassador can register his post for tracking. Either it would be some API or through just some Discord message .
d. Admin should be able to look up data for a date range where he will get a list of ambassadors and under each ambassador a list of posts. Engagement numbers for each post. Also, consolidated engagement for each ambassador. 

3. Users
- Ambassadors or Social Media Influencers 
- These are selective users - 30 to 50 only

4. Features
You decide on the features. This will not be a proper long-term project. This is kind of a script or something to get this data and then incentivize the ambassadors 

5. User Flow
Ambassadors should be able to register their Twitter post for tracking via Discord because the mode of communication is Discord channel. 
Then the tracking will start. 
Our admin should be able to look up the data i.e. engagement numbers for each ambassador for the time duration. 

6. Success Metrics
- Engagement numbers are being tracked accurately 
- Admin is able to look up the engagement numbers for all the ambassadors 

7. Resources
- https://docs.engages.io/ 
- Feel free to try other 3rd party tools

8. Notes
- Intially, admin functionality can be skipped and this lookup can be public.
- For 3rd party dependency, Refreshing data over 1 hour, 6 hours, or even 1 day is fine because we'll be analyzing the track data for a long date range for like a week or month.
