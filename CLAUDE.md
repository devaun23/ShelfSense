# ShelfSense - Claude Code Context

This file provides context for Claude Code sessions working on ShelfSense.

## Project Overview
ShelfSense is an AI-powered adaptive learning platform for medical students preparing for USMLE Step 2 CK.

## Tech Stack
- **Backend**: FastAPI, SQLAlchemy, PostgreSQL (Railway), Redis (caching)
- **Frontend**: Next.js, TypeScript, Tailwind CSS
- **AI**: OpenAI GPT-4o for question generation and tutoring
- **Deployment**: Railway (backend), Netlify (frontend)

## Key Architecture Decisions

### OpenAI Integration
All OpenAI calls go through `backend/app/services/openai_service.py` which provides:
- Circuit breaker pattern (5 failures = OPEN, 120s recovery)
- Exponential backoff with jitter
- Sentry error tracking
- Graceful fallback to cached/database questions

### Caching Strategy
- Redis-based caching via `backend/app/services/cache_service.py`
- 7-day TTL for generated questions
- Cache warming on startup for popular specialties
- Graceful degradation when Redis unavailable

### Rate Limiting
- Daily limits by tier (free: 10 AI questions, student: 50, premium: unlimited)
- Per-minute burst limits to prevent OpenAI rate limit hits
- Implemented in `backend/app/middleware/rate_limiter.py`

## Session Continuity

### Pending Tasks / Next Steps
When ending a session, add incomplete tasks here:

---

## 2025-11-27: Production Hardening Session

### Completed
- [x] Error Handling with circuit breaker (`openai_service.py`)
- [x] Redis-based question caching (`cache_service.py`)
- [x] Burst rate limiting (`rate_limiter.py`)
- [x] Production test suite (`tests/production/`)
- [x] GitHub Actions workflow (`production-tests.yml`)
- [x] Fixed `rate_limiter` middleware exports (ImportError bug)
- [x] Set `RAILWAY_URL` GitHub secret
- [x] Production tests passing

### Current Status
- 🟢 **Railway API**: https://shelfsense-production-d135.up.railway.app (healthy)
- 🟢 **Production Tests**: Passing
- 🟢 **Circuit Breaker**: Implemented
- 🟢 **Rate Limiting**: Tier-based (free/student/premium)
- 🟡 **Caching**: Ready (needs Redis addon)
- 🔴 **CI/CD Pipeline**: Failing (missing `CLERK_PUBLISHABLE_KEY` secret)

### Remaining TODO

#### 1. Add Redis to Railway (Optional - for caching)
Go to https://railway.app/dashboard → ShelfSense project → **"+ New"** → **"Database"** → **"Redis"**

Railway auto-injects `REDIS_URL`. Without Redis, app works but no caching.

#### 2. Fix CI/CD Pipeline (Optional)
Add these GitHub secrets:
- `CLERK_PUBLISHABLE_KEY` - From Clerk dashboard
- `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` - Same value

#### 3. Add Remaining Test Secrets (Optional)
- `TEST_USER_EMAIL` - For authenticated tests
- `TEST_USER_PASSWORD` - For login tests
- `SLACK_WEBHOOK_URL` - For failure notifications

### Key Files Added/Modified This Session
| File | Description |
|------|-------------|
| `backend/app/services/openai_service.py` | Circuit breaker wrapper for OpenAI |
| `backend/app/services/cache_service.py` | Redis-based question caching |
| `backend/app/middleware/rate_limiter.py` | Added OpenAIBurstLimiter class |
| `backend/tests/production/` | Production test suite |
| `.github/workflows/production-tests.yml` | Automated production testing |
| `backend/app/routers/admin.py` | Added `/openai-status` endpoint |

### Related Plan File
`.claude/plans/ethereal-booping-quail.md` - Full implementation plan

---

## Common Commands

### Run Backend Locally
```bash
cd backend
source venv/bin/activate  # or .venv/bin/activate
uvicorn app.main:app --reload
```

### Run Tests
```bash
cd backend
pytest tests/ -v
pytest tests/production/ -v  # Requires RAILWAY_URL env var
```

### Type Check
```bash
cd backend
npx pyright  # or mypy app/
```

## Important Notes
- Always use `openai_service.chat_completion()` instead of direct OpenAI calls
- Check `question_cache.is_connected` before assuming Redis is available
- Production tests require environment variables to be set
