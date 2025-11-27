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

## 2024-11-27: Production Hardening Session

### Completed
- [x] Error Handling with circuit breaker (`openai_service.py`)
- [x] Redis-based question caching (`cache_service.py`)
- [x] Burst rate limiting (`rate_limiter.py`)
- [x] Production test suite (`tests/production/`)
- [x] GitHub Actions workflow (`production-tests.yml`)

### Next Steps (TODO)

#### 1. Railway Redis Setup
```bash
railway add redis
```
This will automatically inject `REDIS_URL` into the environment.

#### 2. GitHub Secrets Configuration
Add these secrets to the repository settings (Settings > Secrets and variables > Actions):
- `RAILWAY_URL` - Your Railway deployment URL (e.g., `https://shelfsense-backend.up.railway.app`)
- `TEST_USER_EMAIL` - Email for a test user account
- `TEST_USER_PASSWORD` - Password for the test user
- `TEST_USER_ID` - (Optional) Test user's ID
- `SLACK_WEBHOOK_URL` - (Optional) For failure notifications

#### 3. Verify Deployment
After deploying:
1. Check health: `curl https://your-railway-url.up.railway.app/health`
2. Check circuit breaker status (admin): `GET /api/admin/openai-status`
3. Check cache stats (when Redis is connected)

#### 4. Run Production Tests Manually
```bash
RAILWAY_URL=https://your-url.up.railway.app \
TEST_USER_EMAIL=test@example.com \
TEST_USER_PASSWORD=yourpassword \
pytest backend/tests/production/ -v
```

#### 5. Monitor Success Metrics
- **Error Handling**: Zero unhandled 500 errors from OpenAI failures
- **Caching**: 80%+ cache hit rate, <100ms for cached responses
- **Overall Latency**: 95% of requests under 3 seconds
- **Rate Limiting**: Proper 429 responses with Retry-After headers
- **Testing**: All 12+ learning engine endpoints passing

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
