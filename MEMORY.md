# JARVIS Memory

## User Profile
- Platform: Windows PC (primary), Oracle Cloud ARM64 VM (secondary)
- User focus: finance tech, Meridian project, autonomous agent orchestration
- Style: concise, no unnecessary explanation, wants persistence without recklessness

## Meridian Project
- Finance job application tracker: React 19, Vite 8, TypeScript, Tailwind, Zustand, Dexie
- Backend: Node.js on Render free tier (512MB RAM)
- Frontend: Vercel
- SQLite DB: 60.6MB, 6299 jobs, 370 companies
- GitHub: KENo548/meridian (private)
- Branches: main (production), staging

## Jarvis Architecture
- 8 core agents + on-demand specialist skills
- OpenCode 1.18.30 on PC and Oracle VM (upgraded from 1.17.4)
- Oracle VM: 130.61.60.47, port 4096
- GitHub as sync layer between PC and Oracle

## Operational Patterns
- Lazy DB initialization: opens on first query
- JWT auth: httpOnly cookie, 7-day expiry, sub-millisecond /api/auth/me
- Startup pipeline disabled on cold start; cron handles ingestion
- Instant logout: clear local, fire server call in background
- Auto-retry for cold starts: 3x with backoff

## Known Issues
- Eightfold anti-bot protection on Render
- SuccessFactors URLs returning 404/500
- Vercel staging auto-deploy not triggering
- Gmail SMTP requires App Password from Google
