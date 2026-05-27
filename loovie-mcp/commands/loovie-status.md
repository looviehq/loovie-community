---
description: Show the user's Loovie projects and any in-flight jobs.
---

Give the user a quick status snapshot:

1. Call `list_projects` and show the 5 most recently updated by title + last-modified.
2. Call `list_generation_history` (limit 10) for any in-flight or recently completed generations. Group by status (running / queued / done / failed).
3. Read `loovie://credits` and show the current balance.

Format the result as a short bulleted summary. Do not start any new generations.
