---
description: Show the user's current Loovie credit balance and recent spend.
---

Read `loovie://credits` and show the user:

- Current balance (integer credits).
- The 5 most recent ledger entries (date, tool that spent, credits).

If the balance is below 50, suggest opening the Loovie mobile app to top up (see https://loovie.app). Do not start any new generations.
