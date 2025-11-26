# ShelfSense Platform Design

## Design Philosophy
Clean, minimalistic, distraction-free interface optimized for focused study sessions.

## Color Palette

### Primary Colors
- **Background**: Pure Black `#000000`
- **Text**: Pure White `#FFFFFF`
- **Progress Bar**: Navy Blue `#1E3A5F`
- **Accent**: Navy Blue `#1E3A5F`

### UI States
- **Correct Answer**: Emerald `#10B981`
- **Incorrect Answer**: Red `#EF4444`
- **Hover**: Navy Blue `#2C5282` (slightly lighter)
- **Disabled**: Gray `#6B7280`

## Progress Bar Specifications

### Positioning
- **Location**: Fixed at top of viewport (superior position)
- **z-index**: 9999 (always visible, above all content)

### Styling
- **Height**: 2px (ultra-thin, sleek)
- **Width**: Dynamic based on completion percentage
- **Color**: Navy Blue `#1E3A5F`
- **Animation**: Smooth width transition (300ms ease-out)
- **Background**: Transparent or subtle gray `#1F1F1F`

### Behavior
- Updates in real-time as questions are answered
- Smooth transitions between percentages
- No text labels (pure visual indicator)
- Glows slightly on hover (optional: `box-shadow: 0 0 8px #1E3A5F`)

## Tech Stack

### Frontend
- **Framework**: Next.js 14 (App Router)
- **Styling**: Tailwind CSS with custom black theme
- **State Management**: React Context + Zustand
- **UI Components**: Headless UI + custom components
- **Animations**: Framer Motion (minimal, purposeful)

### Backend
- **API**: FastAPI (Python)
- **Database**: PostgreSQL (user data, tracking)
- **Question Storage**: JSON files → PostgreSQL on first run
- **Authentication**: JWT tokens
- **ORM**: SQLAlchemy

### Deployment
- **Frontend**: Vercel (Next.js)
- **Backend**: Railway or Render
- **Database**: Railway PostgreSQL or Supabase

## Database Schema

### Users Table
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    target_score INTEGER,
    exam_date DATE
);
```

### Questions Table
```sql
CREATE TABLE questions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vignette TEXT NOT NULL,
    answer_key TEXT NOT NULL,
    choices JSONB NOT NULL,
    explanation TEXT,
    source VARCHAR(255),
    recency_tier INTEGER,
    recency_weight DECIMAL(3,2),
    metadata JSONB
);
```

### Question Attempts Table
```sql
CREATE TABLE question_attempts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    question_id UUID REFERENCES questions(id),
    user_answer TEXT,
    is_correct BOOLEAN,
    time_spent_seconds INTEGER,
    hover_events JSONB,
    scroll_events JSONB,
    confidence_level INTEGER,
    attempted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, question_id, attempted_at)
);
```

### User Performance Table
```sql
CREATE TABLE user_performance (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    session_date DATE,
    questions_answered INTEGER,
    accuracy_overall DECIMAL(5,2),
    accuracy_weighted DECIMAL(5,2),
    predicted_score INTEGER,
    weak_areas JSONB,
    strong_areas JSONB,
    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## UI Components

### 1. Progress Bar Component
```tsx
// Superior position, 2px height, navy blue
<div className="fixed top-0 left-0 right-0 h-[2px] bg-gray-900 z-[9999]">
  <div
    className="h-full bg-[#1E3A5F] transition-all duration-300 ease-out"
    style={{ width: `${progress}%` }}
  />
</div>
```

### 2. Question Display
- **Layout**: Single column, centered, max-width 800px
- **Vignette**: Large text (18px), line-height 1.8
- **Choices**: Radio buttons, full-width, 16px text
- **Spacing**: Generous padding (24px between elements)

### 3. Answer Feedback
- **Correct**: Green border-left accent (4px), "Correct" text
- **Incorrect**: Red border-left accent (4px), show correct answer
- **Explanation**: Collapsible section below feedback

### 4. Navigation
- **Minimal**: No traditional navbar
- **Controls**: Floating "Next" button (bottom right)
- **Menu**: Hamburger icon (top right) for settings/stats

## User Flow

### First Time User
1. Landing page (black background, navy blue CTA)
2. Sign up (email + password)
3. Set target score + exam date
4. Algorithm calibration (5 random questions)
5. Enter adaptive learning mode

### Returning User
1. Auto-login (JWT)
2. Dashboard shows:
   - Current predicted score
   - Questions answered today
   - Progress bar (overall completion)
   - "Continue" button
3. Resume adaptive learning

### Question Session
1. Progress bar at top (superior position, 2px, navy blue)
2. Question vignette displayed
3. User selects answer
4. Behavioral tracking (silent):
   - Time on question
   - Hover events on choices
   - Scroll events
   - Time to select answer
5. Submit answer
6. Immediate feedback (green/red)
7. Explanation + First Aid link
8. "Next Question" button
9. Progress bar updates smoothly

## Adaptive Algorithm Flow

### Question Selection
```python
def select_next_question(user_id):
    # 1. Get user's weak areas (< 60% accuracy)
    weak_areas = get_weak_areas(user_id)

    # 2. Get unanswered questions in weak areas
    pool = get_unanswered_questions(user_id, weak_areas)

    # 3. Apply recency weighting (newer = higher priority)
    weighted_pool = apply_recency_weights(pool)

    # 4. Select from top 20% of weighted pool (randomized)
    return random.choice(weighted_pool[:int(len(weighted_pool) * 0.2)])
```

### Performance Prediction
```python
def calculate_predicted_score(user_id):
    # Get all attempts with recency weighting
    attempts = get_all_attempts(user_id)

    # Weighted accuracy = sum(correct * weight) / sum(weight)
    weighted_accuracy = sum(
        attempt.is_correct * attempt.question.recency_weight
        for attempt in attempts
    ) / sum(attempt.question.recency_weight for attempt in attempts)

    # Map to Step 2 CK score (194-300 range)
    # 60% = 194 (fail), 75% = 245 (average), 90% = 270+
    predicted_score = 194 + (weighted_accuracy - 0.6) * 265

    return round(predicted_score)
```

## File Structure

```
ShelfSense/
├── frontend/                 # Next.js app
│   ├── app/
│   │   ├── layout.tsx       # Root layout (black theme)
│   │   ├── page.tsx         # Landing page
│   │   ├── auth/
│   │   │   ├── login/
│   │   │   └── signup/
│   │   ├── dashboard/
│   │   │   └── page.tsx     # User dashboard
│   │   └── study/
│   │       └── page.tsx     # Question session
│   ├── components/
│   │   ├── ProgressBar.tsx  # Navy blue, 2px, superior
│   │   ├── Question.tsx
│   │   ├── AnswerChoice.tsx
│   │   └── Feedback.tsx
│   ├── lib/
│   │   ├── api.ts           # API client
│   │   └── store.ts         # Zustand store
│   ├── tailwind.config.ts   # Custom black theme
│   └── package.json
├── backend/                  # FastAPI app
│   ├── main.py              # FastAPI entry point
│   ├── models.py            # SQLAlchemy models
│   ├── schemas.py           # Pydantic schemas
│   ├── database.py          # DB connection
│   ├── routers/
│   │   ├── auth.py          # Auth endpoints
│   │   ├── questions.py     # Question endpoints
│   │   └── analytics.py     # Performance endpoints
│   ├── services/
│   │   ├── adaptive.py      # Adaptive algorithm
│   │   └── tracking.py      # Behavioral tracking
│   └── requirements.txt
├── data/
│   ├── shelfsense_master_database.json  # 2,001 questions
│   └── first_aid_knowledge_base.json
└── scripts/
    └── load_questions_to_db.py  # One-time data load
```

## Tailwind Config (Black Theme)

```typescript
// tailwind.config.ts
export default {
  theme: {
    extend: {
      colors: {
        navy: {
          DEFAULT: '#1E3A5F',
          light: '#2C5282',
          dark: '#0F1E3F',
        },
      },
      backgroundColor: {
        primary: '#000000',
      },
      textColor: {
        primary: '#FFFFFF',
      },
    },
  },
}
```

## Performance Requirements

- **Initial Load**: < 2 seconds
- **Question Transition**: < 300ms
- **Progress Bar Animation**: 300ms smooth transition
- **API Response**: < 500ms (question fetch)
- **Database Queries**: < 100ms (indexed queries)

## Behavioral Tracking (Silent)

### Metrics Collected
1. **Time to Answer**: Milliseconds from question display to submission
2. **Hover Events**: Which choices were hovered over (indicates consideration)
3. **Scroll Events**: Scroll position during reading (indicates thoroughness)
4. **Choice Changes**: Number of times user changed selection (indicates uncertainty)
5. **Confidence Level**: Optional user input (1-5 scale)

### Privacy
- All tracking data belongs to user
- No third-party analytics
- User can export/delete all data
- Used ONLY for adaptive algorithm improvement

## Next Steps

1. ✅ Design specifications complete
2. Set up Next.js frontend project
3. Set up FastAPI backend project
4. Create PostgreSQL database
5. Load 2,001 questions into database
6. Implement adaptive algorithm
7. Build UI components
8. Integrate First Aid knowledge
9. Deploy locally and test
10. Deploy to production
