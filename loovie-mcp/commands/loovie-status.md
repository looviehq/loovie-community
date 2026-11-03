---
description: Show the user's Loovie projects and recent generations.
---

Give the user a quick status snapshot:

1. Call `list_projects` and show the 5 most recently updated by title + last-modified.
2. Call `list_generation_history` (limit 10) for the 10 most recent completed generations, labelled by type (image / video). It is a history of finished assets, not a job queue: there is no tool that lists in-flight jobs. If the user asks about a specific running job, poll it with `get_job` using a job id you already have.
3. Read `loovie://credits` and show the current balance.

Format the result as a short bulleted summary. Do not start any new generations.
