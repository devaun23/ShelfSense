# ShelfPass - Claude Code Context

This file provides context for Claude Code sessions working on ShelfPass.

## Project Overview
ShelfPass is an AI-powered adaptive learning platform for medical students preparing for USMLE Step 2 CK.

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

## Design Rules (MUST FOLLOW)

### No Emojis
Never include emojis anywhere in the UI, buttons, icons, or design elements. This is a permanent rule for the entire application.

### No Hyphens in Text
Never use hyphens (—, -, –) in user-facing text content. Use commas, periods, or line breaks instead. This applies to:
- Marketing copy and descriptions
- Loading messages and feedback
- Button labels and headings
- All UI text throughout the application

### Consistent Loading Animation
Always use the spinning circles animation (LoadingSpinner component) for any loading states or stalls in the app. Located at `frontend/components/ui/LoadingSpinner.tsx`.

### OBGYN Spelling
The specialty name must always be spelled "OBGYN" (not "OB-GYN", "OB/GYN", or "Ob-Gyn"). This applies to:
- Frontend display names
- Backend specialty lists
- Test files
- API parameters

---

## MVP Development Strategy (CRITICAL)

### Focus: Internal Medicine Only
For MVP, **only Internal Medicine (IM)** is active. All other specialties are visible but disabled on the homepage with "(soon)" labels.

### Portal Architecture
All specialty portals share the same components:
- `frontend/app/portal/[specialty]/page.tsx` - Dashboard
- `frontend/app/portal/[specialty]/study/page.tsx` - Study mode
- `frontend/app/portal/[specialty]/analytics/page.tsx` - Analytics
- `frontend/app/portal/[specialty]/reviews/page.tsx` - Spaced repetition
- `frontend/app/portal/[specialty]/weak-areas/page.tsx` - Weak areas
- `frontend/components/PortalSidebar.tsx` - Shared sidebar

**Any changes made to the IM portal automatically apply to all other specialty portals** since they use the same dynamic route components. When other specialties are re-enabled, they will have all the same features.

### Core Features to Perfect (MVP)
1. **Study Flow** - Question display, answer selection, feedback, explanations
2. **Analytics** - Accuracy, predicted score, weak areas identification
3. **Spaced Repetition** - Review scheduling, learning stages
4. **AI Explanations** - Quality, completeness, patient-specific reasoning

### Re-enabling Other Specialties
When ready to enable other specialties, update `frontend/app/page.tsx`:
```tsx
// Change this line to add more enabled specialties:
const isEnabled = exam.id === 'internal-medicine';
// To:
const isEnabled = ['internal-medicine', 'surgery', 'pediatrics'].includes(exam.id);
```

### Why This Approach
- Concentrate effort on perfecting one specialty's experience
- Shared components mean no duplicate work
- Quality > Quantity for launch
- Users get a polished IM experience rather than half-baked multi-specialty

---

## Automatic Agent Workflow (MUST FOLLOW)

Claude MUST automatically invoke these agents without waiting for user request:

### After EVERY Code Edit
- **`protective-code-reviewer`** - Run immediately after writing/editing any code
  - Security vulnerabilities, correctness issues, best practices
  - Beginner-friendly explanations of any issues found

### Security-Sensitive Code (auth, API, database, user data)
- **`security-auditor`** - Deep security analysis in addition to code reviewer
  - Authentication flows, API endpoints, data handling
  - OWASP Top 10 checks, injection prevention

### Medical Education Features
- **`medical-education-expert`** - Question design, NBME patterns, learning algorithms
  - Invoke when designing question formats, explanations, difficulty curves
- **`medical-education-architect`** - System design, database schema, API boundaries
  - Invoke when adding new tables, services, or major features
- **`medical-question-pipeline`** - Question ingestion, parsing, NLP tagging
  - Invoke when processing/importing questions
- **`adaptive-learning-algorithm`** - Spaced repetition, question selection, plateau detection
  - Invoke when working on learning algorithms or question selection logic

### Testing & Quality
- **`medical-education-tester`** - Medical accuracy, algorithm validation, load testing
  - Invoke when writing tests or validating educational content

### Compliance
- **`medical-education-compliance`** - HIPAA/FERPA review
  - Invoke when handling student data, PII, or educational records

### Product & Business
- **`entrepreneur`** - Market analysis, product strategy
- **`monetization`** - Revenue models, pricing
  - Invoke when discussing business decisions or feature prioritization

### User Management
- **`user_management`** - Account features, auth flows
- **`testing_qa`** - QA protocols
  - Invoke when building user-facing account features

### Study & Learning Analytics
- **`cognitive-pattern-detector`** - After every 20 questions answered
  - Analyze decision-making patterns, identify failure modes
  - Auto-deploy to provide ongoing pattern analysis
- **`performance-tracker`** - At session start/end
  - Load baseline metrics, capture breakthroughs, document trajectory
  - Deploy when user asks about progress or improvement
- **`score-trajectory-predictor`** - After 50+ questions, then every 20 more
  - Generate three-tier predictions (pessimistic/realistic/optimistic)
  - Deploy before scheduled exams for pre-exam reports
- **`intervention-designer`** - When pattern detector finds >70% failure rate
  - Design targeted learning protocols for specific vulnerabilities
  - Weekly proactive deployment for emerging patterns

### Question Quality Assurance
- **`medical-fact-verifier`** - Before any AI-generated question reaches users
  - Validate clinical accuracy, check treatment guidelines
  - Auto-deploy as safety checkpoint for new content
- **`nbme-pattern-validator`** - For every new AI question + weekly batch validation
  - Ensure questions match real NBME patterns
  - Flag unrealistic or off-pattern questions

### Product & Engineering Planning
- **`mvp-feature-prioritizer`** - During sprint planning, when scope creep detected
  - Ruthlessly prioritize for maximum impact
  - Kill low-value work before it consumes resources
- **`product-definition`** - When raw product ideas need structuring
  - Transform concepts into validated product definitions
  - Define problem, ICP, MVP scope, success metrics
- **`market-customer-research`** - When validating ideas or understanding market
  - Competitor analysis, customer profiles, validation plans
- **`technical-architect`** - Converting specs to technical implementation
  - System architecture, tech selection, data models, API contracts
- **`project-roadmap-builder`** - After planning, before implementation
  - Transform plans into actionable 90-day roadmaps with sprints
- **`ux-ui-designer`** - When designing new features or improving UX
  - User flows, wireframes, interaction patterns, copy guidelines
- **`engineering-architect`** - For comprehensive development plans
  - Full-stack architecture, CI/CD, testing strategies, launch readiness
- **`gtm-growth-strategist`** - Pre-launch and growth planning
  - Positioning, acquisition channels, onboarding funnels, retention

### Invocation Pattern
```
1. Complete the requested code/feature
2. Immediately invoke relevant agent(s) using Task tool
3. Report agent findings to user
4. Fix any issues found before considering task complete
```
