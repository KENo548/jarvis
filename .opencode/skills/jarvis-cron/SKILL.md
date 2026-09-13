---
name: jarvis-cron
description: Scheduled task management, cron job setup, and periodic task execution.
license: MIT
metadata:
  domain: infra
  complexity: low
---

# Cron Jobs

## What I do

- Scheduled task setup
- Cron expression design
- Periodic task management
- Job monitoring and logging

## When to use me

Use this skill for cron job setup, scheduled tasks, or periodic execution.

## Patterns

### Cron Expression
```
# Every 10 minutes
*/10 * * * *

# Every hour
0 * * * *

# Daily at midnight
0 0 * * *

# Weekly on Monday
0 0 * * 1
```

### Health Check Cron
```bash
# Keep-alive ping
*/10 * * * * curl -s https://your-app.onrender.com/api/health > /dev/null 2>&1
```

### Backup Cron
```bash
# Daily backup
0 2 * * * /path/to/backup.sh >> /var/log/backup.log 2>&1
```

## Anti-patterns

- Don't run too frequent jobs (min 1 min)
- Don't skip logging
- Don't ignore job failures
- Don't use overlapping jobs

---
*Source: Extracted from jarvis cron capabilities*
