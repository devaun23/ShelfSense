# 📋 ShelfSense GitHub Issues - Comprehensive Action Plan

This document contains all GitHub issues to be created for ShelfSense project organization. Copy each issue into GitHub Issues with the specified labels and priorities.

---

## 🚨 CRITICAL PRIORITY (P0) - Fix Immediately

### Issue #1: Remove Debug Endpoints from Production

**Labels:** `security`, `critical`, `backend`

**Description:**
Debug endpoints are currently exposed in production at `/debug/db-stats` and `/debug/test-openai`, which leak sensitive information including API key prefixes and database structure.

**Current Behavior:**
- `/debug/db-stats` exposes: database URL, OpenAI API key prefix, question counts
- `/debug/test-openai` exposes: OpenAI API key prefix, makes unnecessary API calls

**Security Risk:**
- **HIGH** - Attackers can gather reconnaissance data about infrastructure
- Exposes API key patterns which could aid in brute force attacks
- Reveals internal database structure

**Expected Behavior:**
- Debug endpoints should be disabled in production
- If needed, require admin authentication
- Never expose API keys or credentials (even prefixes)

**Acceptance Criteria:**
- [ ] Remove `/debug/db-stats` and `/debug/test-openai` endpoints
- [ ] OR add environment-based guards (only in development)
- [ ] OR add admin-only authentication
- [ ] Verify endpoints return 404 in production
- [ ] Add security note to documentation

**Files to Modify:**
- `backend/app/main.py` (lines 54-120)

**Priority:** P0 (Critical)
**Estimated Time:** 15 minutes

---

### Issue #2: Fix Authentication Security - Implement Password Requirement

**Labels:** `security`, `critical`, `backend`, `authentication`

**Description:**
Currently, the User model has `password_hash` as nullable, allowing users to be created without passwords. This is a major security vulnerability.

**Current Code:**
```python
# backend/app/models/models.py:17
password_hash = Column(String, nullable=True)  # Made optional for simple registration
```

**Security Risk:**
- **CRITICAL** - Users can authenticate without credentials
- No protection against unauthorized access
- Not production-ready

**Expected Behavior:**
- All users must have passwords
- Passwords must be hashed using bcrypt
- Implement password strength requirements
- Add password reset flow

**Acceptance Criteria:**
- [ ] Change `password_hash` to `nullable=False`
- [ ] Add password validation (min 8 chars, requires uppercase, lowercase, number)
- [ ] Implement proper password hashing with bcrypt
- [ ] Add password reset endpoint
- [ ] Write tests for authentication flows
- [ ] Update frontend login/signup to include password field
- [ ] Add migration to require passwords for existing users

**Files to Modify:**
- `backend/app/models/models.py`
- `backend/app/routers/users.py`
- `frontend/app/login/page.tsx`
- Create: `backend/alembic/versions/add_password_requirement.py`

**Priority:** P0 (Critical - Blocks production launch)
**Estimated Time:** 2 hours

---

### Issue #3: Audit and Secure CORS Configuration

**Labels:** `security`, `high`, `backend`

**Description:**
Current CORS configuration uses wildcard patterns for Netlify domains which could allow attacks from malicious Netlify-hosted sites.

**Current Code:**
```python
allow_origins=[
    "http://localhost:3000",
    "https://shelfsense99.netlify.app",
    "https://*.netlify.app",  # ⚠️ Too permissive
]
```

**Security Risk:**
- **MEDIUM-HIGH** - Wildcard allows ANY Netlify subdomain
- Potential CSRF attacks from malicious actors using Netlify
- Cross-origin data leakage

**Expected Behavior:**
- Only allow specific, verified origins
- Use environment variables for allowed origins
- Document CORS policy

**Acceptance Criteria:**
- [ ] Replace wildcard with explicit preview URL pattern
- [ ] Move allowed origins to environment variables
- [ ] Add origin validation middleware
- [ ] Document CORS configuration in README
- [ ] Add tests for CORS headers

**Files to Modify:**
- `backend/app/main.py` (line 25)
- Create: `backend/.env.example`

**Priority:** P0 (High)
**Estimated Time:** 30 minutes

---

## 🔴 HIGH PRIORITY (P1) - Fix Within 24 Hours

### Issue #4: Add Comprehensive Test Suite

**Labels:** `testing`, `high`, `backend`, `frontend`

**Description:**
Currently, the project has **0% test coverage**. No unit tests, integration tests, or E2E tests exist for the application code.

**Why This Matters:**
- Cannot safely refactor code
- No regression detection
- High risk of breaking changes
- Not production-ready

**Expected Outcome:**
- **Frontend:** 80%+ test coverage
- **Backend:** 80%+ test coverage
- CI pipeline runs tests automatically
- Tests run locally before commits

**Acceptance Criteria:**

**Frontend (Jest + React Testing Library):**
- [ ] Set up Jest and React Testing Library
- [ ] Test `QuestionCard` component (selection, submission)
- [ ] Test `AIChat` component (message sending, display)
- [ ] Test `Sidebar` component (navigation, collapsing)
- [ ] Test `ProgressBar` component (percentage calculation)
- [ ] Test study page (question flow, timer)
- [ ] Test API integration (mocked endpoints)
- [ ] Add `npm test` script to package.json

**Backend (Pytest):**
- [ ] Set up Pytest with fixtures
- [ ] Test question CRUD endpoints
- [ ] Test AI generation (mocked OpenAI)
- [ ] Test spaced repetition algorithm
- [ ] Test adaptive learning weights
- [ ] Test chat endpoints
- [ ] Test authentication flows
- [ ] Test error handling
- [ ] Add `pytest` to requirements.txt

**Infrastructure:**
- [ ] Create `/frontend/tests/` directory structure
- [ ] Create `/backend/app/tests/` directory structure
- [ ] Add test fixtures and mocks
- [ ] Configure coverage reporting (codecov.io)
- [ ] Add GitHub Actions workflow for tests

**Files to Create:**
- `frontend/jest.config.js`
- `frontend/tests/setup.ts`
- `frontend/tests/components/QuestionCard.test.tsx`
- `backend/pytest.ini`
- `backend/app/tests/conftest.py`
- `backend/app/tests/test_questions.py`
- `.github/workflows/test.yml`

**Priority:** P1 (High)
**Estimated Time:** 8 hours

---

### Issue #5: Set Up CI/CD Pipeline

**Labels:** `infrastructure`, `high`, `devops`

**Description:**
No automated CI/CD pipeline exists. All deployments are manual, and code quality checks don't run automatically.

**Current State:**
- Manual deployments only
- No automated testing
- No code quality checks
- No security scanning

**Expected Outcome:**
- Every PR triggers automated checks
- Main branch auto-deploys to production
- Failed checks block merging
- Security vulnerabilities detected automatically

**Acceptance Criteria:**

**GitHub Actions Workflows:**

1. **Quality Checks** (`.github/workflows/quality.yml`)
   - [ ] Run ESLint on frontend
   - [ ] Run TypeScript type checking
   - [ ] Run Black formatter check on backend
   - [ ] Run Flake8 linter on backend
   - [ ] Check for console.logs in code
   - [ ] Verify no hardcoded secrets

2. **Test Suite** (`.github/workflows/test.yml`)
   - [ ] Run frontend tests with coverage
   - [ ] Run backend tests with coverage
   - [ ] Upload coverage to Codecov
   - [ ] Fail if coverage drops below 80%

3. **Security Scan** (`.github/workflows/security.yml`)
   - [ ] Run npm audit (frontend dependencies)
   - [ ] Run safety check (Python dependencies)
   - [ ] Run Snyk security scan
   - [ ] Check for exposed secrets

4. **Deploy** (`.github/workflows/deploy.yml`)
   - [ ] Build frontend (Next.js)
   - [ ] Build backend (FastAPI)
   - [ ] Deploy to Railway (backend) on main push
   - [ ] Deploy to Netlify (frontend) on main push
   - [ ] Run smoke tests after deployment

**Branch Protection:**
- [ ] Require PR reviews before merging
- [ ] Require status checks to pass
- [ ] Require branch to be up to date
- [ ] No direct pushes to main

**Files to Create:**
- `.github/workflows/quality.yml`
- `.github/workflows/test.yml`
- `.github/workflows/security.yml`
- `.github/workflows/deploy.yml`
- `.github/CODEOWNERS`

**Priority:** P1 (High)
**Estimated Time:** 4 hours

---

### Issue #6: Implement Error Monitoring and Logging

**Labels:** `observability`, `high`, `backend`, `frontend`

**Description:**
No error tracking or monitoring exists. Production errors are invisible, making debugging nearly impossible.

**Current State:**
- No error tracking service
- Basic Python logging only
- No way to know if users hit errors
- No performance monitoring

**Expected Outcome:**
- Real-time error tracking
- Automatic error notifications
- Performance monitoring
- User session replay for debugging

**Acceptance Criteria:**

**Frontend (Sentry):**
- [ ] Install `@sentry/nextjs`
- [ ] Configure Sentry in Next.js
- [ ] Add error boundaries to key components
- [ ] Track JavaScript errors automatically
- [ ] Add breadcrumbs for user actions
- [ ] Set up source maps for debugging
- [ ] Configure release tracking

**Backend (Sentry + Structured Logging):**
- [ ] Install `sentry-sdk[fastapi]`
- [ ] Configure Sentry for FastAPI
- [ ] Add structured JSON logging
- [ ] Log all API errors with context
- [ ] Add request ID tracking
- [ ] Set up log aggregation (Logtail/Datadog)
- [ ] Create logging standards document

**Monitoring Setup:**
- [ ] Create Sentry project (free tier)
- [ ] Configure error alerting (Slack/email)
- [ ] Set up uptime monitoring (UptimeRobot)
- [ ] Add performance tracking
- [ ] Create monitoring dashboard

**Environment Variables:**
```bash
SENTRY_DSN=your_sentry_dsn_here
SENTRY_ENVIRONMENT=production
LOG_LEVEL=INFO
```

**Files to Modify:**
- `frontend/sentry.client.config.ts` (create)
- `frontend/sentry.server.config.ts` (create)
- `backend/app/logging_config.py` (create)
- `backend/app/main.py` (add Sentry middleware)
- `.env.example`

**Priority:** P1 (High - Critical for production)
**Estimated Time:** 3 hours

---

### Issue #7: Add API Rate Limiting

**Labels:** `security`, `high`, `backend`, `performance`

**Description:**
No rate limiting exists on API endpoints. Vulnerable to:
- Brute force attacks
- API abuse
- OpenAI quota exhaustion
- DDoS attacks

**Current Risk:**
- Unlimited AI question generation (expensive!)
- Unlimited chat messages
- No protection against abuse
- Could exhaust OpenAI quota quickly

**Expected Behavior:**
- Rate limits per user/IP
- Different limits for different endpoints
- Clear error messages when limited
- Automatic blocking of abusers

**Acceptance Criteria:**

**Rate Limiting Strategy:**
```python
# Per-user limits (authenticated)
/api/questions/generate: 20 requests/hour
/api/chat: 50 messages/hour
/api/questions: 1000 requests/hour

# Per-IP limits (unauthenticated)
/api/*: 100 requests/hour
```

**Implementation:**
- [ ] Install `slowapi` package
- [ ] Add rate limiting middleware
- [ ] Configure limits per endpoint
- [ ] Return 429 status code when exceeded
- [ ] Add `Retry-After` header
- [ ] Store rate limit state in Redis (or in-memory for now)
- [ ] Add rate limit info to response headers
- [ ] Create bypass list for admins
- [ ] Log rate limit violations

**Response Format:**
```json
{
  "detail": "Rate limit exceeded",
  "error_code": "RATE_LIMIT_EXCEEDED",
  "retry_after": 3600,
  "limit": 20,
  "remaining": 0,
  "reset_at": "2025-11-26T13:00:00Z"
}
```

**Files to Modify:**
- `backend/app/main.py` (add middleware)
- `backend/app/middleware/rate_limit.py` (create)
- `backend/requirements.txt` (add slowapi)

**Priority:** P1 (High - Protects OpenAI budget)
**Estimated Time:** 2 hours

---

## 🟡 MEDIUM PRIORITY (P2) - Fix Within 1 Week

### Issue #8: Update README with Current Setup Instructions

**Labels:** `documentation`, `medium`, `onboarding`

**Description:**
README is severely outdated. References old architecture (pdfplumber extraction only), doesn't mention deployed app, missing setup instructions.

**Current README Problems:**
- Says "Next steps: Build frontend interface" (frontend exists!)
- No mention of production URLs
- No backend setup instructions
- No environment variable documentation
- Missing technology stack info

**Expected README Sections:**

1. **Project Overview**
   - What is ShelfSense?
   - Key features
   - Live demo links

2. **Tech Stack**
   - Frontend: Next.js 16, React 19, TypeScript, Tailwind CSS
   - Backend: FastAPI, SQLAlchemy, OpenAI API
   - Database: SQLite (production: PostgreSQL recommended)
   - Deployment: Netlify (frontend), Railway (backend)

3. **Local Development Setup**
   ```bash
   # Prerequisites
   # Backend setup
   # Frontend setup
   # Environment variables
   # Running locally
   ```

4. **Project Structure**
   - Directory overview
   - Key files explanation

5. **Testing**
   - Running tests
   - Writing new tests

6. **Deployment**
   - Production URLs
   - Deployment process
   - Environment variables

7. **Contributing**
   - Code style guide
   - Commit message format
   - PR process

8. **Documentation**
   - Link to all .md docs
   - Architecture diagrams

**Acceptance Criteria:**
- [ ] Rewrite README.md with modern content
- [ ] Add badges (build status, coverage, etc.)
- [ ] Include screenshots of UI
- [ ] Add "Quick Start" section (5 minutes to running locally)
- [ ] Document all environment variables
- [ ] Add troubleshooting section
- [ ] Link to related docs (ERRORS_AGENT_SPECIFICATION.md, etc.)

**Files to Modify:**
- `README.md`

**Priority:** P2 (Medium)
**Estimated Time:** 1.5 hours

---

### Issue #9: Create .env.example Files

**Labels:** `documentation`, `medium`, `backend`, `frontend`

**Description:**
No `.env.example` files exist. New developers don't know what environment variables are needed.

**Expected Outcome:**
- Clear `.env.example` files for both frontend and backend
- Documentation of each variable
- Instructions for obtaining API keys

**Acceptance Criteria:**

**Backend `.env.example`:**
```bash
# Database Configuration
DATABASE_URL=sqlite:///./shelfsense.db
# For production, use: postgresql://user:password@host:port/database

# OpenAI Configuration
OPENAI_API_KEY=sk-your-key-here
# Get your key from: https://platform.openai.com/api-keys

# Authentication
SECRET_KEY=your-secret-key-for-jwt
# Generate with: openssl rand -hex 32
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Environment
ENVIRONMENT=development  # development | production
DEBUG=true

# CORS Origins
ALLOWED_ORIGINS=http://localhost:3000,https://shelfsense99.netlify.app

# Error Tracking (Optional)
SENTRY_DSN=
```

**Frontend `.env.example`:**
```bash
# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000
# Production: https://shelfsense-production-d135.up.railway.app

# Environment
NEXT_PUBLIC_ENVIRONMENT=development

# Analytics (Optional)
NEXT_PUBLIC_GOOGLE_ANALYTICS_ID=

# Error Tracking (Optional)
NEXT_PUBLIC_SENTRY_DSN=
```

**Documentation:**
- [ ] Create `backend/.env.example`
- [ ] Create `frontend/.env.example`
- [ ] Add setup instructions to README
- [ ] Document how to get OpenAI API key
- [ ] Add to onboarding checklist

**Files to Create:**
- `backend/.env.example`
- `frontend/.env.example`

**Priority:** P2 (Medium)
**Estimated Time:** 30 minutes

---

### Issue #10: Improve .gitignore for Better Repository Hygiene

**Labels:** `maintenance`, `medium`, `repository`

**Description:**
Current `.gitignore` is minimal. Many files that shouldn't be tracked could be accidentally committed.

**Current .gitignore Issues:**
- Doesn't ignore `.env` files
- Doesn't ignore database files
- Doesn't ignore build outputs
- Doesn't ignore IDE files

**Expected .gitignore Additions:**

```gitignore
# Environment Variables
.env
.env.local
.env.production
.env.*.local

# Dependencies
node_modules/
__pycache__/
*.py[cod]
*$py.class
.Python
env/
venv/
ENV/

# Build Outputs
.next/
out/
dist/
build/
*.egg-info/

# Databases (local dev only)
*.db
*.sqlite
*.sqlite3
shelfsense.db

# IDEs
.vscode/
.idea/
*.swp
*.swo
*.swn
.DS_Store

# Logs
*.log
npm-debug.log*
yarn-debug.log*
yarn-error.log*

# Testing
coverage/
.pytest_cache/
.coverage
htmlcov/

# Data files (if large - consider Git LFS)
data/extracted_questions/*.json
data/compressed_pdfs/*.pdf

# OS
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db

# Misc
.turbo
.vercel
.railway
```

**Acceptance Criteria:**
- [ ] Update `.gitignore` with comprehensive rules
- [ ] Verify no sensitive files are currently tracked
- [ ] Remove any tracked files that should be ignored
- [ ] Document in README which files should never be committed

**Files to Modify:**
- `.gitignore`

**Priority:** P2 (Medium)
**Estimated Time:** 15 minutes

---

### Issue #11: Organize Documentation into /docs Directory

**Labels:** `documentation`, `medium`, `organization`

**Description:**
Currently 17+ markdown files in root directory. Makes repository cluttered and hard to navigate.

**Current Structure:**
```
/
├── README.md
├── PROJECT_STATUS.md
├── PLATFORM_DESIGN.md
├── NBME_MASTERY_GUIDE.md
├── AGENT_GENERATION_GUIDE.md
├── ... (13 more .md files)
```

**Proposed Structure:**
```
/
├── README.md (keep in root)
├── CONTRIBUTING.md (keep in root)
├── LICENSE.md (keep in root)
└── docs/
    ├── architecture/
    │   ├── PLATFORM_DESIGN.md
    │   ├── ADAPTIVE_IMPROVEMENT.md
    │   └── BEHAVIORAL_TRACKING.md
    ├── guides/
    │   ├── AGENT_GENERATION_GUIDE.md
    │   ├── NBME_MASTERY_GUIDE.md
    │   └── QUALITY_ASSURANCE_PLAN.md
    ├── plans/
    │   ├── PROJECT_ROADMAP.md
    │   ├── PROJECT_STATUS.md
    │   ├── DEPLOYMENT_STATUS.md
    │   └── ERRORS_AGENT_SPECIFICATION.md
    ├── technical/
    │   ├── EXTRACTION_STATUS.md
    │   ├── EXPLANATION_FRAMEWORK.md
    │   └── QUESTION_WEIGHTING_STRATEGY.md
    └── sessions/
        └── SESSION_SUMMARY.md
```

**Acceptance Criteria:**
- [ ] Create `/docs` directory with subdirectories
- [ ] Move all documentation files to appropriate subdirectories
- [ ] Update all internal links between docs
- [ ] Update README to link to docs
- [ ] Create `docs/README.md` as documentation index
- [ ] Update any scripts that reference old paths

**Files to Move:**
- 15+ markdown files

**Priority:** P2 (Medium)
**Estimated Time:** 1 hour

---

### Issue #12: Add TypeScript Path Aliases for Cleaner Imports

**Labels:** `frontend`, `medium`, `dx`, `refactor`

**Description:**
Currently using relative imports like `../../components/AIChat`. Should use path aliases for cleaner, more maintainable code.

**Current Imports:**
```typescript
import { AIChat } from '../../components/AIChat'
import { Sidebar } from '../../components/Sidebar'
import { API_URL } from '../../../lib/constants'
```

**Desired Imports:**
```typescript
import { AIChat } from '@/components/AIChat'
import { Sidebar } from '@/components/Sidebar'
import { API_URL } from '@/lib/constants'
```

**Configuration Needed:**

**tsconfig.json** (already has some):
```json
{
  "compilerOptions": {
    "paths": {
      "@/*": ["./*"],
      "@/components/*": ["./components/*"],
      "@/lib/*": ["./lib/*"],
      "@/types/*": ["./types/*"],
      "@/hooks/*": ["./hooks/*"],
      "@/app/*": ["./app/*"]
    }
  }
}
```

**Acceptance Criteria:**
- [ ] Update `tsconfig.json` with comprehensive path aliases
- [ ] Refactor all imports to use `@/` prefix
- [ ] Update ESLint to understand path aliases
- [ ] Document path alias patterns in CONTRIBUTING.md
- [ ] Verify build still works

**Files to Modify:**
- `frontend/tsconfig.json`
- All `.tsx`/`.ts` files in frontend (global find/replace)

**Priority:** P2 (Medium)
**Estimated Time:** 1 hour

---

### Issue #13: Add Pre-commit Hooks for Code Quality

**Labels:** `developer-experience`, `medium`, `quality`

**Description:**
No pre-commit hooks exist. Developers can commit code that violates standards.

**Expected Outcome:**
- Automatic code formatting before commit
- Linting errors block commits
- Tests run before push
- No console.logs in commits

**Tools:**
- **Husky** - Git hooks manager
- **lint-staged** - Run linters on staged files only
- **Prettier** - Code formatting
- **ESLint** - JavaScript/TypeScript linting

**Acceptance Criteria:**

**Frontend Hooks:**
```json
// package.json
{
  "husky": {
    "hooks": {
      "pre-commit": "lint-staged",
      "pre-push": "npm run type-check && npm test"
    }
  },
  "lint-staged": {
    "*.{ts,tsx}": [
      "eslint --fix",
      "prettier --write"
    ],
    "*.{json,md}": [
      "prettier --write"
    ]
  }
}
```

**Backend Hooks:**
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    hooks:
      - id: black
        language_version: python3.11

  - repo: https://github.com/pycqa/flake8
    hooks:
      - id: flake8
        args: [--max-line-length=88]

  - repo: https://github.com/pre-commit/mirrors-mypy
    hooks:
      - id: mypy
        additional_dependencies: [types-all]
```

**Installation:**
- [ ] Install Husky: `npm install --save-dev husky lint-staged`
- [ ] Install pre-commit (Python): `pip install pre-commit`
- [ ] Configure hooks
- [ ] Test hooks with dummy commits
- [ ] Document in README
- [ ] Add setup to onboarding

**Files to Create:**
- `.husky/pre-commit`
- `.husky/pre-push`
- `.pre-commit-config.yaml`

**Files to Modify:**
- `frontend/package.json`
- `backend/requirements.txt`

**Priority:** P2 (Medium)
**Estimated Time:** 1.5 hours

---

## 🟢 LOW PRIORITY (P3) - Fix When Convenient

### Issue #14: Add API Documentation with OpenAPI/Swagger

**Labels:** `documentation`, `low`, `backend`, `api`

**Description:**
FastAPI auto-generates OpenAPI docs at `/docs`, but they're not customized or comprehensive.

**Expected Outcome:**
- Comprehensive API documentation
- Example requests/responses
- Authentication instructions
- Rate limit documentation

**Acceptance Criteria:**
- [ ] Add detailed docstrings to all endpoints
- [ ] Add request/response examples
- [ ] Document authentication flow
- [ ] Add Redoc alternative at `/redoc`
- [ ] Customize OpenAPI schema metadata
- [ ] Add API versioning strategy
- [ ] Create Postman collection
- [ ] Add API changelog

**Example:**
```python
@router.post(
    "/questions/generate",
    response_model=QuestionResponse,
    summary="Generate AI question",
    description="Generates a novel USMLE-style question using AI",
    responses={
        201: {"description": "Question generated successfully"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "AI generation failed"}
    }
)
async def generate_question(
    specialty: str = Query(..., description="Medical specialty", example="Internal Medicine"),
    difficulty: float = Query(0.65, ge=0.5, le=0.8, description="Target difficulty"),
    db: Session = Depends(get_db)
) -> QuestionResponse:
    """
    Generate a new AI-powered USMLE Step 2 CK question.

    This endpoint uses OpenAI's GPT-4o to create realistic clinical vignettes
    following NBME Gold Book principles.

    **Rate Limits:**
    - Authenticated: 20 requests/hour
    - Unauthenticated: Not allowed

    **Example Response:**
    ```json
    {
      "id": 1234,
      "vignette": "A 45-year-old man...",
      "choices": ["A", "B", "C", "D", "E"],
      "specialty": "Internal Medicine"
    }
    ```
    """
```

**Priority:** P3 (Low)
**Estimated Time:** 3 hours

---

### Issue #15: Migrate from SQLite to PostgreSQL for Production

**Labels:** `database`, `low`, `scalability`, `backend`

**Description:**
Currently using SQLite (5.1MB file-based database). Not ideal for production at scale.

**Why Migrate:**
- Better concurrency (multiple writers)
- Better performance for complex queries
- More robust for production workloads
- Better support for concurrent users
- Built-in replication and backup

**Current State:**
```python
DATABASE_URL = "sqlite:///./shelfsense.db"
```

**Target State:**
```python
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/shelfsense")
```

**Migration Plan:**

1. **Setup PostgreSQL**
   - [ ] Create Railway PostgreSQL instance
   - [ ] Get connection string
   - [ ] Update environment variables

2. **Data Migration**
   - [ ] Export SQLite data to JSON
   - [ ] Create PostgreSQL tables
   - [ ] Import data to PostgreSQL
   - [ ] Verify data integrity

3. **Code Changes**
   - [ ] Update DATABASE_URL
   - [ ] Add `psycopg2-binary` to requirements
   - [ ] Test all queries with PostgreSQL
   - [ ] Add connection pooling
   - [ ] Update documentation

4. **Performance Optimization**
   - [ ] Add database indexes
   - [ ] Analyze query performance
   - [ ] Set up connection pooling
   - [ ] Configure backup strategy

**Acceptance Criteria:**
- [ ] PostgreSQL running on Railway
- [ ] All data migrated successfully
- [ ] All tests passing with PostgreSQL
- [ ] Performance equal or better than SQLite
- [ ] Backup/restore procedure documented

**Files to Modify:**
- `backend/app/database.py`
- `backend/requirements.txt`
- `.env.example`

**Priority:** P3 (Low - SQLite fine for now)
**Estimated Time:** 3 hours

---

### Issue #16: Optimize Frontend Bundle Size

**Labels:** `performance`, `low`, `frontend`

**Description:**
Haven't measured bundle size yet. Should optimize for faster page loads.

**Expected Outcome:**
- Measure baseline bundle size
- Implement code splitting
- Lazy load components
- Reduce initial load time

**Analysis Tools:**
```bash
npm run build
# Check .next/analyze output

npx @next/bundle-analyzer
```

**Optimization Strategies:**
- [ ] Analyze bundle with `@next/bundle-analyzer`
- [ ] Implement dynamic imports for large components
- [ ] Lazy load AI chat component
- [ ] Code split by route
- [ ] Remove unused dependencies
- [ ] Use React.lazy() for non-critical components
- [ ] Optimize images (if any added)
- [ ] Enable SWC minification

**Target Metrics:**
- First Contentful Paint: <1.5s
- Largest Contentful Paint: <2.5s
- Time to Interactive: <3.0s
- Bundle size: <200KB (gzipped)

**Acceptance Criteria:**
- [ ] Bundle analysis report generated
- [ ] Lighthouse score >90
- [ ] Initial bundle <200KB
- [ ] Routes code-split
- [ ] Non-critical components lazy loaded

**Priority:** P3 (Low - No performance issues yet)
**Estimated Time:** 2 hours

---

### Issue #17: Add Database Indexes for Query Optimization

**Labels:** `performance`, `low`, `backend`, `database`

**Description:**
No custom indexes defined. As database grows, queries may slow down.

**Current State:**
- Only default primary key indexes
- No indexes on foreign keys
- No indexes on filtered columns

**Recommended Indexes:**

```python
# Questions table
- specialty (frequently filtered)
- source (for filtering AI vs NBME)
- created_at (for ordering)

# QuestionAttempts table
- user_id (foreign key, frequently joined)
- question_id (foreign key, frequently joined)
- created_at (for date range queries)
- is_correct (for accuracy calculations)

# ScheduledReviews table
- user_id (foreign key)
- due_date (frequently filtered and ordered)
- learning_stage (for grouping)

# ChatMessages table
- question_id (foreign key)
- user_id (foreign key)
- created_at (for ordering)
```

**Implementation:**
```python
# In models.py
class Question(Base):
    __tablename__ = "questions"

    # Add indexes
    __table_args__ = (
        Index('ix_question_specialty', 'specialty'),
        Index('ix_question_source', 'source'),
        Index('ix_question_created', 'created_at'),
    )
```

**Acceptance Criteria:**
- [ ] Analyze slow query log (once generated)
- [ ] Add indexes to frequently queried columns
- [ ] Create Alembic migration for indexes
- [ ] Benchmark query performance before/after
- [ ] Document indexing strategy

**Priority:** P3 (Low - Database still small)
**Estimated Time:** 1.5 hours

---

### Issue #18: Add Automated Dependency Updates with Dependabot

**Labels:** `maintenance`, `low`, `security`

**Description:**
Dependencies can become outdated quickly. Automate update PRs.

**Expected Outcome:**
- Weekly automated PRs for dependency updates
- Security vulnerabilities auto-detected
- Easier to keep dependencies fresh

**Configuration:**

```yaml
# .github/dependabot.yml
version: 2
updates:
  # Frontend dependencies
  - package-ecosystem: "npm"
    directory: "/frontend"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 5
    labels:
      - "dependencies"
      - "frontend"

  # Backend dependencies
  - package-ecosystem: "pip"
    directory: "/backend"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 5
    labels:
      - "dependencies"
      - "backend"

  # GitHub Actions
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
    labels:
      - "dependencies"
      - "ci"
```

**Acceptance Criteria:**
- [ ] Create `.github/dependabot.yml`
- [ ] Verify Dependabot PRs are created
- [ ] Set up auto-merge for patch updates (optional)
- [ ] Document dependency update process
- [ ] Configure security alerts

**Priority:** P3 (Low)
**Estimated Time:** 20 minutes

---

## 📊 Project Organization Issues

### Issue #19: Create Project Roadmap in GitHub Projects

**Labels:** `project-management`, `organization`

**Description:**
Use GitHub Projects to visualize progress and plan sprints.

**Expected Outcome:**
- Clear project board with columns
- All issues categorized
- Sprint planning visible
- Progress tracking

**Acceptance Criteria:**
- [ ] Create GitHub Project board
- [ ] Add columns: Backlog, To Do, In Progress, In Review, Done
- [ ] Add all issues to board
- [ ] Categorize by priority (P0, P1, P2, P3)
- [ ] Create milestones for phases
- [ ] Link to README

**Milestones:**
1. **MVP Security** (P0 issues)
2. **Production Ready** (P1 issues)
3. **Polish & Optimization** (P2 issues)
4. **Future Enhancements** (P3 issues)

**Priority:** Medium
**Estimated Time:** 1 hour

---

### Issue #20: Create CONTRIBUTING.md Guide

**Labels:** `documentation`, `onboarding`

**Description:**
No contribution guidelines exist for new developers.

**Expected Sections:**

1. **Getting Started**
   - Local setup
   - Running dev servers
   - Running tests

2. **Code Style**
   - TypeScript conventions
   - Python conventions
   - Naming patterns

3. **Git Workflow**
   - Branch naming
   - Commit messages
   - PR process
   - Code review guidelines

4. **Testing Requirements**
   - Write tests for new features
   - Maintain >80% coverage
   - Test naming conventions

5. **Documentation**
   - When to update docs
   - How to write good docs

**Acceptance Criteria:**
- [ ] Create `CONTRIBUTING.md`
- [ ] Document code style
- [ ] Document git workflow
- [ ] Add PR template (`.github/pull_request_template.md`)
- [ ] Add issue templates
- [ ] Link from README

**Priority:** Medium
**Estimated Time:** 2 hours

---

## 🎯 Summary by Priority

### P0 (Critical) - 3 issues
1. Remove debug endpoints
2. Fix authentication security
3. Audit CORS configuration

**Total time: ~2.75 hours**

### P1 (High) - 4 issues
4. Add comprehensive test suite
5. Set up CI/CD pipeline
6. Implement error monitoring
7. Add API rate limiting

**Total time: ~17 hours**

### P2 (Medium) - 6 issues
8. Update README
9. Create .env.example
10. Improve .gitignore
11. Organize docs
12. Add TypeScript path aliases
13. Add pre-commit hooks

**Total time: ~6.5 hours**

### P3 (Low) - 5 issues
14. Add API documentation
15. Migrate to PostgreSQL
16. Optimize bundle size
17. Add database indexes
18. Automated dependency updates

**Total time: ~10 hours**

### Organization - 2 issues
19. Create GitHub Projects board
20. Create CONTRIBUTING.md

**Total time: ~3 hours**

---

## 📝 Next Steps

1. **Create these issues in GitHub** - Copy each issue into GitHub Issues
2. **Add labels** - Create labels: security, critical, high, medium, low, backend, frontend, etc.
3. **Create milestones** - Group issues by launch phases
4. **Set up Projects board** - Visualize progress
5. **Start with P0** - Fix critical security issues first
6. **Weekly reviews** - Check progress every Friday

---

**Total Issues:** 20
**Total Estimated Time:** ~39 hours
**Recommended Sprint Length:** 2-3 weeks

**Last Updated:** 2025-11-26
