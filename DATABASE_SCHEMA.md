# ShelfSense Database Schema

## Overview

ShelfSense uses SQLite for local development and supports PostgreSQL for production. The schema is designed for:
- Adaptive learning with spaced repetition
- AI-powered question generation and analytics
- Content management with version control
- User authentication and subscription management

## Entity Relationship Diagram

```
┌─────────────┐       ┌─────────────────────┐       ┌───────────────┐
│   Users     │───────│  QuestionAttempts   │───────│   Questions   │
└─────────────┘       └─────────────────────┘       └───────────────┘
      │                         │                          │
      │                         │                          │
      ▼                         ▼                          ▼
┌─────────────┐       ┌─────────────────────┐       ┌───────────────┐
│ UserSettings│       │    ErrorAnalysis    │       │QuestionRatings│
└─────────────┘       └─────────────────────┘       └───────────────┘
      │                                                    │
      ▼                                                    ▼
┌─────────────┐                                    ┌───────────────┐
│Subscriptions│                                    │ContentVersions│
└─────────────┘                                    └───────────────┘
```

## Core Tables

### Users
Primary user account table with authentication and profile data.

| Column | Type | Description |
|--------|------|-------------|
| id | VARCHAR (PK) | UUID primary key |
| email | VARCHAR (UNIQUE) | User email, indexed |
| first_name | VARCHAR | First name, indexed |
| full_name | VARCHAR | Full display name |
| password_hash | VARCHAR | Hashed password (nullable for OAuth) |
| email_verified | BOOLEAN | Email verification status |
| target_score | INTEGER | Goal USMLE score (200-280) |
| exam_date | DATETIME | Target exam date |
| failed_login_attempts | INTEGER | Security: failed logins |
| locked_until | DATETIME | Security: account lockout |
| created_at | DATETIME | Account creation |
| last_login | DATETIME | Last login timestamp |
| updated_at | DATETIME | Last update timestamp |

**Indexes:**
- `ix_users_email` (UNIQUE) - Login lookup
- `ix_users_first_name` - Name search

### Questions
Question bank with content management and quality metrics.

| Column | Type | Description |
|--------|------|-------------|
| id | VARCHAR (PK) | UUID primary key |
| vignette | TEXT | Clinical scenario text |
| choices | JSON | Answer choices array |
| answer_key | VARCHAR | Correct answer (A-E) |
| explanation | JSON | Framework-based explanation |
| source | VARCHAR | Origin (e.g., "NBME Form 6") |
| specialty | VARCHAR | Normalized specialty |
| difficulty_level | VARCHAR | easy/medium/hard |
| recency_weight | FLOAT | Recency scoring weight |
| content_status | VARCHAR | draft/active/archived |
| source_type | VARCHAR | nbme/ai_generated/imported |
| quality_score | FLOAT | Composite quality (0-100) |
| expert_reviewed | BOOLEAN | Expert verification flag |
| version | INTEGER | Content version number |
| rejected | BOOLEAN | User rejection flag |
| created_at | DATETIME | Creation timestamp |

**Indexes:**
- `ix_questions_source` - Filter by source
- `ix_questions_specialty` - Filter by specialty
- `ix_questions_difficulty_level` - Filter by difficulty
- `ix_questions_quality_score` - Sort by quality
- `ix_questions_recency_weight` - Sort by recency
- `ix_questions_source_weight` (composite) - Specialty + recency queries

### QuestionAttempts
Records each question answer attempt with behavioral data.

| Column | Type | Description |
|--------|------|-------------|
| id | VARCHAR (PK) | UUID primary key |
| user_id | VARCHAR (FK) | Reference to users |
| question_id | VARCHAR (FK) | Reference to questions |
| user_answer | VARCHAR | User's selected answer |
| is_correct | BOOLEAN | Correctness flag |
| time_spent_seconds | INTEGER | Time to answer |
| confidence_level | INTEGER | 1-5 confidence rating |
| hover_events | JSON | Mouse tracking data |
| scroll_events | JSON | Scroll behavior data |
| attempted_at | DATETIME | Attempt timestamp |

**Indexes:**
- `ix_attempts_user_id` - User's attempts
- `ix_attempts_question_id` - Question statistics
- `ix_attempts_is_correct` - Accuracy calculations
- `ix_attempts_attempted_at` - Time-based queries
- `ix_attempts_user_correct` (composite) - Accuracy by user
- `ix_attempts_user_date` (composite) - Trend analysis
- `ix_attempts_user_question` (composite) - Unique attempt lookup

## Learning & Analytics Tables

### ScheduledReviews
Spaced repetition scheduling for questions.

| Column | Type | Description |
|--------|------|-------------|
| user_id | VARCHAR (FK) | User reference |
| question_id | VARCHAR (FK) | Question reference |
| scheduled_for | DATETIME | Next review date |
| review_interval | VARCHAR | Interval (1d, 3d, 7d, etc.) |
| learning_stage | VARCHAR | New/Learning/Review/Mastered |
| times_reviewed | INTEGER | Review count |

**Indexes:**
- `ix_reviews_user_scheduled` (composite) - Due reviews lookup
- `ix_reviews_user_question` (composite) - Existing schedule check

### ErrorAnalysis
AI-powered categorization of incorrect answers.

| Column | Type | Description |
|--------|------|-------------|
| attempt_id | VARCHAR (FK) | Link to attempt |
| user_id | VARCHAR (FK) | User reference |
| error_type | VARCHAR | knowledge_gap, premature_closure, etc. |
| confidence | FLOAT | AI categorization confidence |
| explanation | TEXT | Why the error occurred |
| missed_detail | TEXT | Key fact missed |
| coaching_question | TEXT | Socratic follow-up |

**Indexes:**
- `ix_errors_user_type` (composite) - Error pattern analysis

### LearningMetricsCache
Cached analytics to reduce computation.

| Column | Type | Description |
|--------|------|-------------|
| user_id | VARCHAR (FK) | User reference |
| velocity_score | FLOAT | Learning speed (0-100) |
| calibration_score | FLOAT | Confidence calibration |
| predicted_score | INTEGER | Predicted USMLE score |
| weak_areas | JSON | Areas needing improvement |
| is_stale | BOOLEAN | Cache invalidation flag |

## Content Management Tables

### ContentVersions
Version history for question edits.

| Column | Type | Description |
|--------|------|-------------|
| question_id | VARCHAR (FK) | Question reference |
| version_number | INTEGER | Sequential version |
| vignette_snapshot | TEXT | Content at this version |
| choices_snapshot | JSON | Choices at this version |
| change_type | VARCHAR | created/edited/regenerated |
| changed_by | VARCHAR (FK) | User who made change |
| fields_changed | JSON | List of changed fields |

### ReviewQueue
Content review workflow management.

| Column | Type | Description |
|--------|------|-------------|
| question_id | VARCHAR (FK) | Question in review |
| status | VARCHAR | pending/in_review/approved/rejected |
| priority | INTEGER | Review priority (1-10) |
| assigned_to | VARCHAR (FK) | Assigned reviewer |
| clinical_accuracy_score | INTEGER | 1-5 quality score |
| decision | VARCHAR | approve/reject/revise |

### ContentFreshnessScores
Content relevance and decay tracking.

| Column | Type | Description |
|--------|------|-------------|
| question_id | VARCHAR (FK) | Question reference |
| freshness_score | FLOAT | Current freshness (0-100) |
| discrimination_index | FLOAT | Skill differentiation ability |
| difficulty_index | FLOAT | Actual difficulty from data |
| needs_review | BOOLEAN | Flagged for review |

## Monetization Tables

### Subscriptions
User subscription management.

| Column | Type | Description |
|--------|------|-------------|
| user_id | VARCHAR (FK) | User reference |
| tier | VARCHAR | free/student/premium |
| started_at | DATETIME | Subscription start |
| expires_at | DATETIME | Expiration date |
| stripe_customer_id | VARCHAR | Stripe integration |

### DailyUsage
Rate limiting and usage tracking.

| Column | Type | Description |
|--------|------|-------------|
| user_id | VARCHAR (FK) | User reference |
| date | DATETIME | Usage date |
| questions_answered | INTEGER | Daily question count |
| ai_chat_messages | INTEGER | Daily AI messages |
| ai_questions_generated | INTEGER | Daily AI questions |

## Session & Study Tables

### StudySession
Groups attempts into named study sessions.

| Column | Type | Description |
|--------|------|-------------|
| user_id | VARCHAR (FK) | User reference |
| mode | VARCHAR | practice/timed/tutor/review |
| specialty | VARCHAR | Filter specialty |
| target_count | INTEGER | Target questions |
| time_limit_seconds | INTEGER | For timed mode |
| questions_answered | INTEGER | Progress count |
| accuracy | FLOAT | Session accuracy |
| status | VARCHAR | active/paused/completed |

### FlaggedQuestions
User-marked questions for review.

| Column | Type | Description |
|--------|------|-------------|
| user_id | VARCHAR (FK) | User reference |
| question_id | VARCHAR (FK) | Flagged question |
| flag_reason | VARCHAR | Why flagged |
| custom_note | TEXT | User's note |
| folder | VARCHAR | Organization tag |
| priority | INTEGER | Review priority |

## Index Strategy

### Single-Column Indexes
Used for simple WHERE clause filtering:
```sql
CREATE INDEX ix_questions_source ON questions(source);
CREATE INDEX ix_questions_specialty ON questions(specialty);
CREATE INDEX ix_attempts_user_id ON question_attempts(user_id);
```

### Composite Indexes
Optimized for common multi-column queries:

```sql
-- Accuracy calculation: WHERE user_id = ? AND is_correct = true
CREATE INDEX ix_attempts_user_correct ON question_attempts(user_id, is_correct);

-- Trend analysis: WHERE user_id = ? ORDER BY attempted_at
CREATE INDEX ix_attempts_user_date ON question_attempts(user_id, attempted_at);

-- Due reviews: WHERE user_id = ? AND scheduled_for <= ?
CREATE INDEX ix_reviews_user_scheduled ON scheduled_reviews(user_id, scheduled_for);

-- Error patterns: WHERE user_id = ? GROUP BY error_type
CREATE INDEX ix_errors_user_type ON error_analyses(user_id, error_type);
```

## Migration Strategy

### Adding New Columns
SQLite doesn't support all ALTER TABLE operations. For new columns:

```python
def add_column_if_missing(cursor, table, column, column_def):
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [row[1] for row in cursor.fetchall()]
    if column not in columns:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_def}")
```

### Running Migrations
```bash
cd backend
python3 -m migrations.migrate_database
```

## Performance Considerations

### Query Optimization
1. **Use indexes** for WHERE, ORDER BY, and JOIN columns
2. **Composite indexes** follow leftmost prefix rule
3. **LIMIT queries** for pagination
4. **Avoid SELECT *** - specify needed columns

### Caching Strategy
- `LearningMetricsCache` stores computed analytics
- Cache invalidated when new attempts added (`is_stale = true`)
- Background job recalculates stale caches

### Scaling to PostgreSQL
The schema is designed to work with both SQLite and PostgreSQL:
- Use VARCHAR instead of TEXT for indexed columns
- JSON columns work in both (JSONB preferred in PostgreSQL)
- UUID generation is handled in Python

```python
# In database.py
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./shelfsense.db")
# For production: postgresql://user:password@host/database
```

## Data Integrity

### Foreign Key Constraints
All relationships use proper foreign keys:
```sql
FOREIGN KEY(user_id) REFERENCES users(id)
FOREIGN KEY(question_id) REFERENCES questions(id)
```

### Cascade Behavior
Currently using default RESTRICT. Consider CASCADE for:
- User deletion → all user data
- Question deletion → attempts, ratings, reviews

### Unique Constraints
- `users.email` - One account per email
- `subscriptions.user_id` - One subscription per user
- `user_settings.user_id` - One settings record per user

## Future Enhancements

1. **Full-text search** on question vignettes
2. **Materialized views** for dashboard aggregations
3. **Partitioning** question_attempts by date
4. **Read replicas** for analytics queries
5. **Connection pooling** for production scale
