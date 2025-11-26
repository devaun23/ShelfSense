# 🛡️ ShelfSense Errors Agent Specification

## Purpose

The Errors Agent is an automated quality assurance system that continuously monitors, detects, and reports code quality issues, errors, and technical debt in the ShelfSense codebase. It ensures code remains clean, secure, maintainable, and follows best practices.

---

## Core Responsibilities

### 1. **Error Detection & Monitoring**
- Runtime error tracking (frontend + backend)
- Build failure detection
- Dependency vulnerability scanning
- API endpoint health monitoring
- Database query performance monitoring

### 2. **Code Quality Enforcement**
- TypeScript strict mode compliance
- Python type hints coverage
- Linting rule violations
- Code complexity analysis
- Unused code detection

### 3. **Security Auditing**
- API key exposure prevention
- Authentication vulnerability scanning
- CORS policy validation
- SQL injection risk detection
- XSS vulnerability scanning

### 4. **Documentation Maintenance**
- API documentation completeness
- Code comment quality
- README accuracy
- Setup instruction validation
- Architecture diagram updates

### 5. **Performance Optimization**
- Bundle size monitoring (frontend)
- API response time tracking
- Database query optimization
- Memory leak detection
- Render performance monitoring

---

## Automated Checks

### **Pre-Commit Checks** (Local Development)
```bash
# Frontend checks
npm run lint           # ESLint + TypeScript
npm run build          # Next.js build validation
npm run type-check     # TypeScript strict mode

# Backend checks
black --check .        # Python code formatting
flake8 .              # Python linting
mypy .                # Python type checking
pytest tests/         # Run all tests
```

### **CI/CD Pipeline Checks** (GitHub Actions)
```yaml
# .github/workflows/quality-checks.yml
- Build validation (frontend + backend)
- Test suite execution (unit + integration)
- Security vulnerability scanning
- Code coverage reporting (target: >80%)
- Lighthouse performance audit (target: >90)
```

### **Production Monitoring**
- Error rate alerts (Sentry)
- API uptime monitoring (Railway health endpoint)
- Frontend error tracking (LogRocket)
- OpenAI API quota tracking
- Database size monitoring

---

## Error Classification System

### **Critical (P0)** - Fix Immediately
- Production crashes
- Security vulnerabilities
- Data loss risks
- API authentication failures
- Payment processing errors

### **High (P1)** - Fix Within 24h
- Feature-breaking bugs
- Performance degradation >30%
- Memory leaks
- Database migration failures
- Broken user workflows

### **Medium (P2)** - Fix Within 1 Week
- UI/UX inconsistencies
- Non-critical API errors
- Documentation gaps
- Code duplication
- Missing error handling

### **Low (P3)** - Fix When Convenient
- Code style violations
- Outdated dependencies
- Minor performance optimizations
- Refactoring opportunities
- Technical debt cleanup

---

## Current Audit Results (2025-11-26)

### ✅ **What's Working Well**
1. **Clean Code**
   - No `console.log` statements in production code
   - No TypeScript `any` types found
   - TypeScript strict mode enabled
   - Proper environment variable usage

2. **Good Architecture**
   - Clear separation: frontend (Next.js) + backend (FastAPI)
   - Modular router structure
   - Service layer pattern implemented
   - Database ORM (SQLAlchemy) used properly

3. **Documentation**
   - 17+ markdown documentation files
   - Well-documented features
   - Clear project status tracking

### ⚠️ **Critical Issues Found**

#### **Security Vulnerabilities**
| Issue | Severity | Location | Impact |
|-------|----------|----------|--------|
| Debug endpoints in production | **CRITICAL** | `backend/app/main.py:54-120` | Exposes API key prefix, database structure |
| Nullable password hash | **HIGH** | `backend/app/models/models.py:17` | Authentication bypass risk |
| CORS wildcard for Netlify | **MEDIUM** | `backend/app/main.py:25` | Potential CSRF attacks |
| Hardcoded password example in comments | **LOW** | `backend/app/database.py:10` | Bad practice |

#### **Missing Infrastructure**
| Item | Status | Impact |
|------|--------|--------|
| Test suite | ❌ None | Can't validate changes safely |
| CI/CD pipeline | ❌ None | No automated quality checks |
| Error monitoring | ❌ None | Can't detect production issues |
| Logging system | ⚠️ Basic | Hard to debug issues |
| API rate limiting | ❌ None | Vulnerable to abuse |

#### **Code Quality Issues**
| Issue | Count | Impact |
|-------|-------|--------|
| Outdated README | 1 | Confusing for new developers |
| Missing `.env.example` | 1 | Hard to set up locally |
| No pre-commit hooks | 1 | Inconsistent code quality |
| Missing TypeScript path aliases | 1 | Import paths could be cleaner |
| No API documentation | 1 | Hard to integrate frontend |

#### **Performance Concerns**
| Issue | Impact |
|-------|--------|
| 48MB data directory | Slow git operations |
| 5.1MB SQLite database | Should consider PostgreSQL for production |
| No database indexes documented | Potential slow queries |
| No frontend code splitting config | Large initial bundle size |
| No image optimization | Slow page loads if images added |

---

## Coding Best Practices for ShelfSense

### **TypeScript/React (Frontend)**

#### ✅ DO
```typescript
// Use explicit types
interface QuestionProps {
  vignette: string;
  choices: string[];
  onSubmit: (answer: string) => void;
}

// Use functional components with hooks
export function QuestionCard({ vignette, choices, onSubmit }: QuestionProps) {
  const [selected, setSelected] = useState<string | null>(null);
  // ...
}

// Use descriptive error handling
try {
  const response = await fetch(`${API_URL}/questions`);
  if (!response.ok) {
    throw new Error(`Failed to fetch questions: ${response.statusText}`);
  }
} catch (error) {
  console.error('Question fetch error:', error);
  setError('Unable to load questions. Please try again.');
}

// Use React Query for API calls (future enhancement)
const { data, isLoading, error } = useQuery('questions', fetchQuestions);
```

#### ❌ DON'T
```typescript
// Don't use 'any' type
function handleData(data: any) { } // ❌

// Don't ignore errors silently
fetch('/api/questions').catch(() => {}); // ❌

// Don't use inline styles (use Tailwind)
<div style={{ color: 'red' }}>Error</div> // ❌

// Don't mutate state directly
questions.push(newQuestion); // ❌
setQuestions([...questions, newQuestion]); // ✅
```

### **Python/FastAPI (Backend)**

#### ✅ DO
```python
# Use type hints everywhere
from typing import List, Optional
from pydantic import BaseModel

class Question(BaseModel):
    id: int
    vignette: str
    choices: List[str]
    correct_answer: str
    specialty: Optional[str] = None

# Use dependency injection
from fastapi import Depends
from sqlalchemy.orm import Session

@router.get("/questions/{question_id}")
def get_question(
    question_id: int,
    db: Session = Depends(get_db)
) -> Question:
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    return question

# Use proper logging
import logging
logger = logging.getLogger(__name__)

logger.info(f"Generating AI question for specialty: {specialty}")
logger.error(f"OpenAI API error: {str(e)}", exc_info=True)

# Use environment variables
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    openai_api_key: str
    database_url: str

    class Config:
        env_file = ".env"
```

#### ❌ DON'T
```python
# Don't use bare except
try:
    result = risky_operation()
except:  # ❌ Too broad
    pass

# Don't hardcode secrets
api_key = "sk-..." # ❌

# Don't use print() for logging
print("Generating question...") # ❌
logger.info("Generating question...") # ✅

# Don't return raw database objects
return db.query(User).first() # ❌ Exposes internal structure
return UserSchema.from_orm(user) # ✅ Use Pydantic models
```

### **Git Workflow**

#### ✅ DO
```bash
# Use descriptive branch names
git checkout -b feature/add-question-rating
git checkout -b fix/spaced-repetition-bug
git checkout -b refactor/simplify-adaptive-algo

# Write clear commit messages
git commit -m "Add question rating system with approve/reject functionality"
git commit -m "Fix: Spaced repetition intervals resetting incorrectly"
git commit -m "Refactor: Simplify adaptive learning weight calculation"

# Keep commits atomic (one logical change)
# ✅ Good: Each commit does one thing
git commit -m "Add question rating model"
git commit -m "Add rating API endpoints"
git commit -m "Add rating UI component"

# ❌ Bad: Mixing multiple changes
git commit -m "Add ratings, fix bug, update docs"
```

#### ❌ DON'T
```bash
# Don't commit to main directly
git checkout main
git commit -m "WIP" # ❌

# Don't use vague commit messages
git commit -m "updates" # ❌
git commit -m "fix" # ❌
git commit -m "stuff" # ❌

# Don't commit sensitive data
git add .env # ❌
git add backend/shelfsense.db # ❌ (should be .gitignored)
```

### **API Design**

#### ✅ DO
```python
# Use RESTful conventions
GET    /api/questions              # List questions
GET    /api/questions/{id}         # Get single question
POST   /api/questions              # Create question
PUT    /api/questions/{id}         # Update question
DELETE /api/questions/{id}         # Delete question

# Use proper HTTP status codes
200 OK                  # Successful GET/PUT
201 Created            # Successful POST
204 No Content         # Successful DELETE
400 Bad Request        # Invalid input
401 Unauthorized       # Not authenticated
403 Forbidden          # Not authorized
404 Not Found          # Resource doesn't exist
422 Unprocessable Entity  # Validation error
500 Internal Server Error # Server error

# Return consistent error format
{
  "detail": "Question not found",
  "error_code": "QUESTION_NOT_FOUND",
  "timestamp": "2025-11-26T12:00:00Z"
}
```

#### ❌ DON'T
```python
# Don't use non-standard endpoints
GET /api/getQuestions # ❌ (use GET /api/questions)
POST /api/questions/create # ❌ (use POST /api/questions)

# Don't return 200 for errors
return {"error": "Not found"}, 200 # ❌
raise HTTPException(404, "Not found") # ✅

# Don't expose internal errors to clients
return {"error": str(e)} # ❌ May leak sensitive info
return {"error": "An error occurred"} # ✅ Generic message
logger.error(f"Details: {e}") # ✅ Log details server-side
```

---

## File Organization Standards

### **Recommended Structure**
```
ShelfSense/
├── .github/
│   ├── workflows/          # CI/CD pipelines
│   │   ├── frontend.yml
│   │   ├── backend.yml
│   │   └── quality.yml
│   └── ISSUE_TEMPLATE/     # Issue templates
│
├── frontend/
│   ├── app/                # Next.js app directory
│   │   ├── (auth)/        # Auth-related pages
│   │   ├── (study)/       # Study-related pages
│   │   └── api/           # API routes (if needed)
│   ├── components/
│   │   ├── ui/            # Reusable UI components
│   │   ├── study/         # Study-specific components
│   │   └── shared/        # Shared components
│   ├── lib/               # Utilities and helpers
│   │   ├── api.ts         # API client
│   │   ├── utils.ts       # Utility functions
│   │   └── constants.ts   # App constants
│   ├── types/             # TypeScript type definitions
│   ├── hooks/             # Custom React hooks
│   └── tests/             # Frontend tests
│       ├── unit/
│       ├── integration/
│       └── e2e/
│
├── backend/
│   ├── app/
│   │   ├── routers/       # API route handlers
│   │   ├── services/      # Business logic
│   │   ├── models/        # Database models
│   │   ├── schemas/       # Pydantic schemas
│   │   ├── utils/         # Helper functions
│   │   └── tests/         # Backend tests
│   │       ├── unit/
│   │       ├── integration/
│   │       └── fixtures/
│   ├── alembic/           # Database migrations
│   └── scripts/           # Utility scripts
│
├── docs/                  # Documentation (move .md files here)
│   ├── architecture/
│   ├── api/
│   ├── guides/
│   └── plans/
│
├── data/                  # Data files (consider .gitignore)
│   └── .gitkeep
│
└── scripts/               # Project-wide scripts
    ├── setup.sh
    └── deploy.sh
```

### **What Should Be .gitignored**
```gitignore
# Environment variables
.env
.env.local
.env.production

# Dependencies
node_modules/
__pycache__/
*.pyc

# Build outputs
.next/
dist/
build/

# Databases (local development only)
*.db
*.sqlite
*.sqlite3

# IDE
.vscode/
.idea/
*.swp

# OS
.DS_Store
Thumbs.db

# Logs
*.log
npm-debug.log*

# Data files (if large)
data/extracted_questions/*.json
data/compressed_pdfs/*.pdf

# Temporary files
tmp/
temp/
*.tmp
```

---

## Error Monitoring Setup

### **Frontend (Next.js)**

#### Install Sentry
```bash
npm install @sentry/nextjs
npx @sentry/wizard@latest -i nextjs
```

#### Configure Error Boundaries
```typescript
// components/ErrorBoundary.tsx
import { Component, ReactNode } from 'react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: any) {
    console.error('ErrorBoundary caught:', error, errorInfo);
    // Send to error tracking service
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback || (
        <div className="p-8 text-center">
          <h2 className="text-2xl font-bold text-red-600">Something went wrong</h2>
          <p className="mt-4 text-gray-600">
            We've been notified and are working on a fix.
          </p>
          <button
            onClick={() => this.setState({ hasError: false })}
            className="mt-4 px-4 py-2 bg-blue-600 text-white rounded"
          >
            Try Again
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
```

### **Backend (FastAPI)**

#### Add Structured Logging
```python
# app/logging_config.py
import logging
import sys
from pythonjsonlogger import jsonlogger

def setup_logging():
    """Configure structured JSON logging"""
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    formatter = jsonlogger.JsonFormatter(
        '%(timestamp)s %(level)s %(name)s %(message)s'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger

# Usage in routes
logger = logging.getLogger(__name__)

@router.post("/questions/generate")
async def generate_question(specialty: str):
    logger.info("Question generation started", extra={
        "specialty": specialty,
        "user_id": current_user.id
    })

    try:
        question = await generate_ai_question(specialty)
        logger.info("Question generated successfully", extra={
            "question_id": question.id,
            "generation_time": elapsed_time
        })
        return question
    except Exception as e:
        logger.error("Question generation failed", extra={
            "specialty": specialty,
            "error": str(e)
        }, exc_info=True)
        raise
```

#### Add Global Exception Handler
```python
# app/main.py
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch all unhandled exceptions"""
    logger.error(
        f"Unhandled exception: {exc}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "client_ip": request.client.host
        },
        exc_info=True
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "An internal error occurred",
            "error_code": "INTERNAL_ERROR",
            "timestamp": datetime.utcnow().isoformat()
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors with detailed info"""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": exc.errors(),
            "error_code": "VALIDATION_ERROR"
        }
    )
```

---

## Testing Strategy

### **Frontend Tests (Jest + React Testing Library)**

```typescript
// components/QuestionCard.test.tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { QuestionCard } from './QuestionCard';

describe('QuestionCard', () => {
  const mockQuestion = {
    vignette: 'A 45-year-old man...',
    choices: ['Option A', 'Option B', 'Option C'],
    correctAnswer: 'Option A'
  };

  it('renders question vignette', () => {
    render(<QuestionCard {...mockQuestion} />);
    expect(screen.getByText(/45-year-old man/i)).toBeInTheDocument();
  });

  it('allows selecting an answer', () => {
    const onSubmit = jest.fn();
    render(<QuestionCard {...mockQuestion} onSubmit={onSubmit} />);

    fireEvent.click(screen.getByText('Option A'));
    fireEvent.click(screen.getByText('Submit'));

    expect(onSubmit).toHaveBeenCalledWith('Option A');
  });

  it('shows explanation after submission', async () => {
    render(<QuestionCard {...mockQuestion} />);

    fireEvent.click(screen.getByText('Option A'));
    fireEvent.click(screen.getByText('Submit'));

    expect(await screen.findByText(/Explanation/i)).toBeInTheDocument();
  });
});
```

### **Backend Tests (Pytest + FastAPI TestClient)**

```python
# app/tests/test_questions.py
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db
from .fixtures import test_db, sample_question

client = TestClient(app)

def test_get_question(test_db, sample_question):
    """Test retrieving a single question"""
    response = client.get(f"/api/questions/{sample_question.id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == sample_question.id
    assert data["vignette"] == sample_question.vignette

def test_get_nonexistent_question(test_db):
    """Test 404 for nonexistent question"""
    response = client.get("/api/questions/99999")
    assert response.status_code == 404

def test_generate_ai_question(test_db, monkeypatch):
    """Test AI question generation"""
    # Mock OpenAI API
    def mock_create(*args, **kwargs):
        return MockResponse(content="Generated question")

    monkeypatch.setattr("openai.ChatCompletion.create", mock_create)

    response = client.post("/api/questions/generate", json={
        "specialty": "Internal Medicine"
    })

    assert response.status_code == 201
    assert "vignette" in response.json()

def test_submit_answer(test_db, sample_question):
    """Test submitting an answer"""
    response = client.post("/api/questions/submit", json={
        "question_id": sample_question.id,
        "user_answer": "A",
        "time_spent": 120
    })

    assert response.status_code == 200
    data = response.json()
    assert "is_correct" in data
    assert "explanation" in data
```

---

## Continuous Improvement Process

### **Weekly Checklist**
- [ ] Review error logs (Sentry dashboard)
- [ ] Check API uptime (Railway metrics)
- [ ] Monitor OpenAI API usage (stay under quota)
- [ ] Review database size (consider cleanup)
- [ ] Update dependencies (security patches)
- [ ] Review open GitHub issues
- [ ] Check Lighthouse scores (performance)

### **Monthly Checklist**
- [ ] Security audit (dependency vulnerabilities)
- [ ] Performance audit (API response times)
- [ ] Code coverage review (aim for >80%)
- [ ] Documentation updates
- [ ] Refactoring opportunities
- [ ] User feedback review
- [ ] A/B test results analysis

### **Quarterly Checklist**
- [ ] Architecture review
- [ ] Database optimization
- [ ] Major dependency upgrades
- [ ] Technical debt reduction sprint
- [ ] Disaster recovery test
- [ ] Security penetration test
- [ ] Scalability planning

---

## Agent Activation Commands

### **Run Full Audit**
```bash
# From project root
./scripts/errors-agent-audit.sh

# What it does:
# 1. Runs all linters
# 2. Runs all tests
# 3. Checks for security vulnerabilities
# 4. Generates report in ./audit-results/
# 5. Creates GitHub issues for critical findings
```

### **Fix Auto-Fixable Issues**
```bash
./scripts/errors-agent-fix.sh

# What it does:
# 1. Runs code formatters (Black, Prettier)
# 2. Fixes ESLint auto-fixable issues
# 3. Updates outdated dependencies (minor versions)
# 4. Commits changes with "[Errors Agent]" prefix
```

### **Monitor Production**
```bash
./scripts/errors-agent-monitor.sh

# What it does:
# 1. Checks API health endpoints
# 2. Monitors error rates (Sentry)
# 3. Checks database size
# 4. Monitors OpenAI quota
# 5. Sends alerts if thresholds exceeded
```

---

## Success Metrics

### **Code Quality KPIs**
- Test coverage: **Target >80%** (Currently: 0%)
- Lint errors: **Target: 0** (Currently: TBD)
- Security vulnerabilities: **Target: 0** (Currently: 4 known)
- Build time: **Target: <2 min** (Currently: ~1 min)
- Type safety: **Target: 100%** (Currently: ~95%)

### **Production Health KPIs**
- API uptime: **Target: 99.9%** (Currently: Unknown)
- Error rate: **Target: <0.1%** (Currently: Not tracked)
- P95 response time: **Target: <500ms** (Currently: Unknown)
- Lighthouse score: **Target: >90** (Currently: Not measured)
- User-reported bugs: **Target: <5/month** (Currently: Unknown)

---

## Next Steps

1. **Immediate** (This week)
   - Remove debug endpoints from production
   - Set up basic error logging
   - Create `.env.example` file
   - Update README with current setup instructions

2. **Short-term** (This month)
   - Add test suite (frontend + backend)
   - Set up CI/CD pipeline
   - Implement error monitoring (Sentry)
   - Add API rate limiting

3. **Long-term** (This quarter)
   - Achieve >80% test coverage
   - Set up performance monitoring
   - Implement automated security scanning
   - Create comprehensive API documentation

---

**Last Updated:** 2025-11-26
**Agent Version:** 1.0.0
**Status:** Active Monitoring
