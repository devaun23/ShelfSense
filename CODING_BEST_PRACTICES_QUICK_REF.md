# 📘 ShelfSense Coding Best Practices - Quick Reference

**Version:** 1.0.0
**Last Updated:** 2025-11-26

This is a condensed, practical guide for day-to-day development. For detailed explanations, see `ERRORS_AGENT_SPECIFICATION.md`.

---

## 🎯 Core Principles

1. **Minimalism** - Only write code that's needed right now
2. **Clarity** - Code should be self-explanatory
3. **Safety** - Types, tests, and error handling prevent bugs
4. **Consistency** - Follow existing patterns in the codebase
5. **Security** - Never trust user input, never expose secrets

---

## 🔷 TypeScript/React (Frontend)

### File Naming
```
components/QuestionCard.tsx       ✅ PascalCase for components
lib/api-client.ts                 ✅ kebab-case for utilities
types/question.ts                 ✅ singular nouns
hooks/useQuestionTimer.ts         ✅ use prefix for hooks
```

### Component Structure
```typescript
// ✅ GOOD: Functional component with explicit types
interface QuestionCardProps {
  vignette: string;
  choices: string[];
  onSubmit: (answer: string) => void;
}

export function QuestionCard({ vignette, choices, onSubmit }: QuestionCardProps) {
  const [selected, setSelected] = useState<string | null>(null);

  return (
    <div className="p-4 bg-black text-white">
      {/* Component JSX */}
    </div>
  );
}

// ❌ BAD: No types, arrow function exported awkwardly
export default ({ vignette, choices, onSubmit }: any) => {
  const [selected, setSelected] = useState(null);
  // ...
}
```

### State Management
```typescript
// ✅ GOOD: Descriptive state with proper typing
const [isLoading, setIsLoading] = useState<boolean>(false);
const [error, setError] = useState<string | null>(null);
const [questions, setQuestions] = useState<Question[]>([]);

// ✅ GOOD: Immutable state updates
setQuestions([...questions, newQuestion]);
setQuestions(prev => prev.filter(q => q.id !== deletedId));

// ❌ BAD: Mutating state
questions.push(newQuestion);
setQuestions(questions);
```

### Error Handling
```typescript
// ✅ GOOD: Comprehensive error handling
try {
  const response = await fetch(`${API_URL}/questions/${id}`);

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
  }

  const data = await response.json();
  return data;
} catch (error) {
  console.error('Failed to fetch question:', error);
  setError('Unable to load question. Please try again.');
  // Don't throw - handle gracefully in UI
}

// ❌ BAD: Silent failures
fetch('/api/questions').catch(() => {});
```

### API Calls
```typescript
// ✅ GOOD: Centralized API client
// lib/api.ts
const API_URL = process.env.NEXT_PUBLIC_API_URL;

export async function fetchQuestion(id: number): Promise<Question> {
  const response = await fetch(`${API_URL}/questions/${id}`);
  if (!response.ok) throw new Error('Failed to fetch');
  return response.json();
}

// In component
const question = await fetchQuestion(123);

// ❌ BAD: Inline fetch everywhere
const res = await fetch('http://localhost:8000/questions/123');
```

### Styling
```typescript
// ✅ GOOD: Tailwind utility classes
<button className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded">
  Submit
</button>

// ❌ BAD: Inline styles
<button style={{ padding: '8px 16px', backgroundColor: 'blue' }}>
  Submit
</button>
```

---

## 🐍 Python/FastAPI (Backend)

### File Naming
```
routers/questions.py              ✅ Plural nouns for resource routers
services/question_generator.py    ✅ snake_case
models/user.py                    ✅ Singular model names
```

### Type Hints (ALWAYS!)
```python
# ✅ GOOD: Full type hints
from typing import List, Optional
from pydantic import BaseModel

class Question(BaseModel):
    id: int
    vignette: str
    choices: List[str]
    correct_answer: str
    specialty: Optional[str] = None

def get_question(question_id: int, db: Session) -> Question:
    question = db.query(Question).filter_by(id=question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Not found")
    return question

# ❌ BAD: No type hints
def get_question(question_id, db):
    return db.query(Question).filter_by(id=question_id).first()
```

### Error Handling
```python
# ✅ GOOD: Specific exceptions with logging
import logging
logger = logging.getLogger(__name__)

@router.post("/questions/generate")
async def generate_question(specialty: str, db: Session = Depends(get_db)):
    try:
        question = await generate_ai_question(specialty)
        logger.info(f"Generated question for {specialty}", extra={
            "question_id": question.id
        })
        return question
    except OpenAIError as e:
        logger.error(f"OpenAI API error: {e}", exc_info=True)
        raise HTTPException(status_code=503, detail="AI service unavailable")
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal error")

# ❌ BAD: Bare except, print statements
@router.post("/questions/generate")
async def generate_question(specialty):
    try:
        question = generate_ai_question(specialty)
        print("Generated question")
        return question
    except:
        print("Error occurred")
        return {"error": "Something went wrong"}
```

### Database Queries
```python
# ✅ GOOD: Use ORM, handle not found
question = db.query(Question).filter(Question.id == question_id).first()
if not question:
    raise HTTPException(status_code=404, detail="Question not found")

# ✅ GOOD: Efficient filtering
questions = (
    db.query(Question)
    .filter(Question.specialty == specialty)
    .order_by(Question.created_at.desc())
    .limit(20)
    .all()
)

# ❌ BAD: Raw SQL (unless absolutely necessary)
db.execute("SELECT * FROM questions WHERE id = ?", (question_id,))

# ❌ BAD: Loading all data then filtering in Python
all_questions = db.query(Question).all()
filtered = [q for q in all_questions if q.specialty == specialty]
```

### Pydantic Models
```python
# ✅ GOOD: Separate request/response schemas
class QuestionCreate(BaseModel):
    vignette: str
    choices: List[str]
    correct_answer: str
    specialty: str

class QuestionResponse(BaseModel):
    id: int
    vignette: str
    choices: List[str]
    specialty: str
    created_at: datetime

    class Config:
        from_attributes = True  # Enables ORM mode

# Use in route
@router.post("/questions", response_model=QuestionResponse)
def create_question(question: QuestionCreate, db: Session = Depends(get_db)):
    # ...
```

### Environment Variables
```python
# ✅ GOOD: Pydantic settings
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    openai_api_key: str
    database_url: str
    secret_key: str

    class Config:
        env_file = ".env"

settings = Settings()

# ❌ BAD: Direct os.getenv everywhere
api_key = os.getenv("OPENAI_API_KEY")  # Could be None!
```

---

## 🔒 Security Checklist

### NEVER Do This ❌
```python
# ❌ Hardcode secrets
OPENAI_API_KEY = "sk-..."

# ❌ Expose secrets in responses
return {"api_key": os.getenv("OPENAI_API_KEY")}

# ❌ SQL injection risk
db.execute(f"SELECT * FROM users WHERE name = '{user_input}'")

# ❌ Trust user input
file_path = user_input  # Can be ../../etc/passwd
eval(user_input)        # Never use eval()
```

### ALWAYS Do This ✅
```python
# ✅ Use environment variables
api_key = os.getenv("OPENAI_API_KEY")

# ✅ Validate user input
from pydantic import BaseModel, validator

class UserInput(BaseModel):
    specialty: str

    @validator('specialty')
    def validate_specialty(cls, v):
        allowed = ["Internal Medicine", "Surgery", "Pediatrics"]
        if v not in allowed:
            raise ValueError("Invalid specialty")
        return v

# ✅ Use parameterized queries (ORM does this)
db.query(User).filter(User.name == user_input).first()

# ✅ Sanitize error messages
try:
    # sensitive operation
except Exception as e:
    logger.error(f"Details: {e}")  # Log full details
    raise HTTPException(500, "An error occurred")  # Generic to user
```

---

## 📝 Git Commit Messages

### Format
```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types
- `feat`: New feature
- `fix`: Bug fix
- `refactor`: Code change that neither fixes a bug nor adds a feature
- `docs`: Documentation only
- `style`: Formatting, missing semicolons, etc.
- `test`: Adding tests
- `chore`: Maintenance tasks

### Examples
```bash
✅ GOOD:
feat(study): Add question rating system with approve/reject buttons

- Add QuestionRating component with thumbs up/down
- Add POST /api/questions/rate endpoint
- Store ratings in database
- Hide rejected questions from future sessions

Closes #42

✅ GOOD:
fix(spaced-repetition): Correct interval calculation for failed cards

Previously, failed cards were scheduled for 3 days instead of 1 day.
This caused users to forget concepts before review.

Fixes #38

✅ GOOD:
refactor(adaptive): Simplify weight calculation algorithm

- Remove nested loops
- Use list comprehension
- No functional changes

❌ BAD:
fix: updates

❌ BAD:
Added stuff

❌ BAD:
WIP
```

---

## 🧪 Testing Guidelines

### Frontend Tests
```typescript
// tests/components/QuestionCard.test.tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { QuestionCard } from '@/components/QuestionCard';

describe('QuestionCard', () => {
  const mockQuestion = {
    vignette: 'A 45-year-old man presents with chest pain...',
    choices: ['Option A', 'Option B', 'Option C'],
    correctAnswer: 'Option A'
  };

  it('renders the question vignette', () => {
    render(<QuestionCard {...mockQuestion} />);
    expect(screen.getByText(/45-year-old man/i)).toBeInTheDocument();
  });

  it('allows selecting and submitting an answer', () => {
    const onSubmit = jest.fn();
    render(<QuestionCard {...mockQuestion} onSubmit={onSubmit} />);

    fireEvent.click(screen.getByText('Option A'));
    fireEvent.click(screen.getByRole('button', { name: /submit/i }));

    expect(onSubmit).toHaveBeenCalledWith('Option A');
  });

  it('shows correct/incorrect feedback after submission', async () => {
    render(<QuestionCard {...mockQuestion} />);

    fireEvent.click(screen.getByText('Option A'));
    fireEvent.click(screen.getByRole('button', { name: /submit/i }));

    expect(await screen.findByText(/correct/i)).toBeInTheDocument();
  });
});
```

### Backend Tests
```python
# tests/test_questions.py
import pytest
from fastapi.testclient import TestClient

def test_get_question_success(client, sample_question):
    """Test retrieving an existing question"""
    response = client.get(f"/api/questions/{sample_question.id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == sample_question.id
    assert data["vignette"] == sample_question.vignette

def test_get_question_not_found(client):
    """Test 404 for nonexistent question"""
    response = client.get("/api/questions/99999")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

def test_submit_answer_correct(client, sample_question):
    """Test submitting correct answer"""
    response = client.post("/api/questions/submit", json={
        "question_id": sample_question.id,
        "user_answer": sample_question.correct_answer,
        "time_spent": 120
    })

    assert response.status_code == 200
    data = response.json()
    assert data["is_correct"] is True
```

### Test Naming Convention
```python
# ✅ GOOD: Descriptive test names
def test_user_cannot_submit_answer_twice():
def test_ai_generation_retries_on_validation_failure():
def test_spaced_repetition_resets_interval_on_incorrect_answer():

# ❌ BAD: Vague test names
def test_submit():
def test_generation():
def test_error():
```

---

## 📁 File Organization

### Keep Files Small
```
✅ GOOD:
components/
  ├── QuestionCard.tsx           (150 lines)
  ├── AIChat.tsx                 (200 lines)
  └── Sidebar.tsx                (180 lines)

❌ BAD:
components/
  └── AllComponents.tsx          (2000 lines)
```

### Group Related Files
```
✅ GOOD:
features/
  ├── study/
  │   ├── QuestionCard.tsx
  │   ├── QuestionTimer.tsx
  │   ├── QuestionExplanation.tsx
  │   └── types.ts
  └── chat/
      ├── AIChat.tsx
      ├── ChatMessage.tsx
      └── types.ts

❌ BAD:
components/
  ├── QuestionCard.tsx
  ├── ChatMessage.tsx
  ├── QuestionTimer.tsx
  ├── AIChat.tsx
```

### Import Order
```typescript
// ✅ GOOD: Organized imports
// 1. External libraries
import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';

// 2. Internal modules (absolute paths)
import { QuestionCard } from '@/components/QuestionCard';
import { useQuestionTimer } from '@/hooks/useQuestionTimer';
import { Question } from '@/types/question';

// 3. Relative imports (if needed)
import { helper } from './utils';

// 4. Styles (if not using Tailwind)
import styles from './styles.module.css';
```

---

## 🚫 Common Anti-Patterns to Avoid

### 1. Prop Drilling
```typescript
// ❌ BAD: Passing props through multiple levels
<Page1 user={user}>
  <Page2 user={user}>
    <Page3 user={user}>
      <Component user={user} />

// ✅ GOOD: Use Context
const UserContext = createContext<User | null>(null);

<UserContext.Provider value={user}>
  <Page1>
    <Page2>
      <Page3>
        <Component />  // Uses useContext(UserContext)
```

### 2. Premature Optimization
```typescript
// ❌ BAD: Complex optimization for small array
const filtered = useMemo(
  () => items.filter(item => item.active),
  [items]
);  // Only 5 items!

// ✅ GOOD: Just filter directly
const filtered = items.filter(item => item.active);
```

### 3. Over-Abstraction
```typescript
// ❌ BAD: Unnecessary abstraction
function createButtonClickHandler(text: string) {
  return () => {
    console.log(text);
  };
}
<button onClick={createButtonClickHandler("clicked")}>Click</button>

// ✅ GOOD: Keep it simple
<button onClick={() => console.log("clicked")}>Click</button>
```

### 4. Magic Numbers
```python
# ❌ BAD: What does 0.7 mean?
if score > 0.7:
    return "pass"

# ✅ GOOD: Named constants
PASSING_SCORE = 0.7

if score > PASSING_SCORE:
    return "pass"
```

---

## ✅ Pre-Commit Checklist

Before committing code, verify:

- [ ] Code follows naming conventions
- [ ] All functions have type hints (Python) or types (TypeScript)
- [ ] Error handling is comprehensive
- [ ] No `console.log` or `print()` statements (use proper logging)
- [ ] No hardcoded values (use constants/env vars)
- [ ] Tests written for new functionality
- [ ] All tests pass (`npm test` / `pytest`)
- [ ] No linter errors (`npm run lint` / `flake8`)
- [ ] Commit message is descriptive
- [ ] No sensitive data (API keys, passwords)

---

## 📚 Quick Reference Commands

### Frontend
```bash
npm run dev              # Start dev server
npm run build            # Build for production
npm run lint             # Run ESLint
npm run type-check       # TypeScript type checking
npm test                 # Run tests
```

### Backend
```bash
uvicorn app.main:app --reload       # Start dev server
pytest                              # Run tests
pytest --cov=app tests/             # Run with coverage
black .                             # Format code
flake8 .                            # Lint code
mypy .                              # Type check
```

### Git
```bash
git status                          # Check status
git add .                           # Stage all changes
git commit -m "feat: description"   # Commit with message
git push origin branch-name         # Push to remote
git log --oneline -10               # View recent commits
```

---

## 🎓 Learning Resources

### TypeScript
- [TypeScript Handbook](https://www.typescriptlang.org/docs/handbook/)
- [React TypeScript Cheatsheet](https://react-typescript-cheatsheet.netlify.app/)

### Python
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pydantic Documentation](https://docs.pydantic.dev/)

### Testing
- [Testing Library Docs](https://testing-library.com/docs/react-testing-library/intro/)
- [Pytest Documentation](https://docs.pytest.org/)

---

## 🤝 Getting Help

1. **Check existing docs** - See `docs/` directory
2. **Read error messages carefully** - They usually tell you what's wrong
3. **Use TypeScript/Python language servers** - They catch errors before runtime
4. **Ask for help** - Create a GitHub issue or discussion

---

**Remember:** Code is read 10x more than it's written. Prioritize clarity over cleverness.

**Last Updated:** 2025-11-26
**Maintained by:** Errors Agent
