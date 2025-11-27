# Complete Medium Priority Tasks - Manual Steps

> **GitHub Issue Template** - Copy this to create an issue at https://github.com/YOUR_REPO/issues/new

## Summary
Manual steps remaining after implementing the 4 medium-priority tasks (AI Quality Validation, Database Indexing, Logging & Monitoring, API Documentation).

## Tasks

### 1. Install Frontend Sentry
```bash
cd frontend
npm install @sentry/nextjs
```

### 2. Set Environment Variables

**Backend (.env or Railway):**
```env
REDIS_URL=redis://default:xxx@xxx.railway.app:6379
```

**Frontend (.env.local or Netlify):**
```env
NEXT_PUBLIC_SENTRY_DSN=https://xxx@sentry.io/xxx
```

### 3. Run Database Migration
Create new composite indexes:
```bash
cd backend
python -c "from app.database import engine, Base; Base.metadata.create_all(bind=engine)"
```

### 4. Generate & Validate 100 Test Questions
```bash
cd backend
python -m scripts.generate_100_test_questions --save

# Or dry-run to validate existing questions:
python -m scripts.generate_100_test_questions --dry-run
```

## Related Implementation
All code changes have been completed:
- Composite indexes added to models.py
- Redis caching layer created (cache.py)
- Slow query logging added to database.py
- N+1 query patterns fixed in analytics
- Frontend Sentry config files created
- ErrorBoundary component created
- API documentation tags added to main.py
- Quality validation service created
- Batch generation script created

## Acceptance Criteria
- [ ] Frontend Sentry installed and configured
- [ ] Environment variables set in production
- [ ] Database migration run successfully
- [ ] 100 test questions generated with validation report reviewed

---
**Labels:** `enhancement`
